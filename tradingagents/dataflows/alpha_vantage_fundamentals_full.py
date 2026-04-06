"""
Alpha Vantage 版 get_fundamentals 实现。

从 AV 的 BALANCE_SHEET、INCOME_STATEMENT、CASH_FLOW、EARNINGS 端点获取数据，
结合股价计算估值/盈利/偿债等指标，输出结构化文本报告。

缓存策略：每个 (ticker, endpoint) 一份 JSON 文件，存于 data_cache/bulk/{TICKER}/ 下。
"""

import json
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd

from .alpha_vantage_common import _make_api_request
from .config import get_config


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------

def _cache_path(ticker: str, cache_key: str) -> Path:
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    return cache_dir / "bulk" / ticker.upper() / f"{cache_key}.json"


def _fetch_and_cache_av(ticker: str, av_function: str, cache_key: str) -> dict:
    """从 AV 获取 JSON 数据并缓存。已有缓存时直接读取。"""
    path = _cache_path(ticker, cache_key)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    raw = _make_api_request(av_function, {"symbol": ticker})
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    else:
        data = raw

    # 检查 API 错误
    if isinstance(data, dict) and ("Error Message" in data or "Information" in data):
        return {}

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


# ---------------------------------------------------------------------------
# 数据过滤
# ---------------------------------------------------------------------------

def _safe_float(record: dict, field: str):
    """安全提取数值字段，返回 float 或 None。"""
    val = record.get(field)
    if val is None or val == "None" or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _get_quarterly_before(data: dict, curr_date: str, list_key: str = "quarterlyReports",
                          date_field: str = "fiscalDateEnding") -> list[dict]:
    """从 JSON 中提取 date <= curr_date 的季度记录，按日期降序。

    Args:
        data: AV API 返回的完整 JSON dict
        curr_date: 截止日期 yyyy-mm-dd
        list_key: JSON 中的数组键名 (quarterlyReports / quarterlyEarnings)
        date_field: 用于过滤的日期字段名
    """
    records = data.get(list_key, [])
    if not records or not curr_date:
        return records

    cutoff = datetime.strptime(curr_date, "%Y-%m-%d")
    filtered = []
    for r in records:
        date_str = r.get(date_field, "")
        if not date_str:
            continue
        try:
            record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if record_date <= cutoff:
                filtered.append((record_date, r))
        except (ValueError, TypeError):
            continue

    filtered.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in filtered]


def _get_earnings_before(data: dict, curr_date: str) -> list[dict]:
    """从 EARNINGS 中按 reportedDate 过滤（防数据泄漏）。"""
    records = data.get("quarterlyEarnings", [])
    if not records or not curr_date:
        return records

    cutoff = datetime.strptime(curr_date, "%Y-%m-%d")
    filtered = []
    for r in records:
        date_str = r.get("reportedDate", r.get("fiscalDateEnding", ""))
        if not date_str:
            continue
        try:
            record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if record_date <= cutoff:
                filtered.append((record_date, r))
        except (ValueError, TypeError):
            continue

    filtered.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in filtered]


# ---------------------------------------------------------------------------
# TTM 聚合
# ---------------------------------------------------------------------------

def _compute_ttm(records: list[dict], field: str):
    """取最近 4 个季度求和。不足 4 季返回 None。"""
    if len(records) < 4:
        return None
    total = 0.0
    for r in records[:4]:
        val = _safe_float(r, field)
        if val is None:
            return None
        total += val
    return total


# ---------------------------------------------------------------------------
# 股价获取
# ---------------------------------------------------------------------------

def _get_stock_price(ticker: str, curr_date: str):
    """获取 curr_date 当天（或最近交易日）的收盘价。返回 float 或 None。"""
    try:
        from .interface import route_to_vendor

        end_date = curr_date
        start_dt = datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=10)
        start_date = start_dt.strftime("%Y-%m-%d")

        csv_data = route_to_vendor("get_stock_data", ticker, start_date, end_date)
        if not csv_data or not csv_data.strip():
            return None

        # 去掉注释行
        lines = csv_data.split("\n")
        csv_lines = [l for l in lines if not l.strip().startswith("#") and l.strip()]
        if len(csv_lines) < 2:
            return None

        df = pd.read_csv(StringIO("\n".join(csv_lines)))
        if df.empty:
            return None

        # 找收盘价列
        for col_name in ["adjusted_close", "Adj Close", "close", "Close"]:
            if col_name in df.columns:
                closes = pd.to_numeric(df[col_name], errors="coerce").dropna()
                if not closes.empty:
                    return float(closes.iloc[0])  # 最新一行
    except Exception:
        pass
    return None


def _compute_price_derived(ticker: str, curr_date: str) -> dict:
    """计算 52WeekHigh/Low, 50DMA, 200DMA。"""
    result = {"52WeekHigh": None, "52WeekLow": None, "50DMA": None, "200DMA": None}
    try:
        from .interface import route_to_vendor

        start_dt = datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=370)
        csv_data = route_to_vendor("get_stock_data", ticker, start_dt.strftime("%Y-%m-%d"), curr_date)
        if not csv_data or not csv_data.strip():
            return result

        lines = csv_data.split("\n")
        csv_lines = [l for l in lines if not l.strip().startswith("#") and l.strip()]
        if len(csv_lines) < 2:
            return result

        df = pd.read_csv(StringIO("\n".join(csv_lines)))
        close_col = None
        for col_name in ["adjusted_close", "Adj Close", "close", "Close"]:
            if col_name in df.columns:
                close_col = col_name
                break
        if close_col is None or df.empty:
            return result

        closes = pd.to_numeric(df[close_col], errors="coerce").dropna()
        if closes.empty:
            return result

        result["52WeekHigh"] = round(float(closes.max()), 2)
        result["52WeekLow"] = round(float(closes.min()), 2)
        if len(closes) >= 50:
            result["50DMA"] = round(float(closes.head(50).mean()), 2)
        if len(closes) >= 200:
            result["200DMA"] = round(float(closes.head(200).mean()), 2)
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# 安全除法
# ---------------------------------------------------------------------------

def _safe_div(numerator, denominator):
    """安全除法，任一为 None 或分母为 0 时返回 None。"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------

def _compute_metrics(bs_records: list[dict], is_records: list[dict],
                     cf_records: list[dict], earnings_records: list[dict],
                     stock_price, curr_date: str, ticker: str = "") -> dict:
    """从财报数据计算所有指标。

    Args:
        bs_records: balance sheet 季度记录（最新在前）
        is_records: income statement 季度记录
        cf_records: cashflow 季度记录
        earnings_records: earnings 季度记录
        stock_price: 当前股价 (float or None)
        curr_date: 当前日期
    """
    m = {}  # metrics dict

    # 最新一期 balance sheet
    bs = bs_records[0] if bs_records else {}
    # 最新一期 income statement
    is_latest = is_records[0] if is_records else {}
    # 最新一期 cashflow
    cf_latest = cf_records[0] if cf_records else {}

    # ── 基础数据 ──
    shares = _safe_float(bs, "commonStockSharesOutstanding")
    total_equity = _safe_float(bs, "totalShareholderEquity")
    total_assets = _safe_float(bs, "totalAssets")
    total_current_assets = _safe_float(bs, "totalCurrentAssets")
    total_current_liabilities = _safe_float(bs, "totalCurrentLiabilities")
    short_term_debt = _safe_float(bs, "shortTermDebt") or 0
    long_term_debt = _safe_float(bs, "longTermDebt") or 0
    cash = _safe_float(bs, "cashAndShortTermInvestments")
    if cash is None:
        cash = _safe_float(bs, "cashAndCashEquivalentsAtCarryingValue") or 0
    inventory = _safe_float(bs, "inventory") or 0

    # TTM 聚合
    ttm_net_income = _compute_ttm(is_records, "netIncome")
    ttm_revenue = _compute_ttm(is_records, "totalRevenue")
    ttm_ebitda = _compute_ttm(is_records, "ebitda")
    ttm_interest_expense = _compute_ttm(is_records, "interestExpense")
    ttm_operating_cashflow = _compute_ttm(cf_records, "operatingCashflow")
    ttm_capex = _compute_ttm(cf_records, "capitalExpenditures")

    # TTM FCF
    ttm_fcf = None
    if ttm_operating_cashflow is not None and ttm_capex is not None:
        ttm_fcf = ttm_operating_cashflow - abs(ttm_capex)

    # Market Cap
    market_cap = None
    if stock_price is not None and shares is not None and shares > 0:
        market_cap = stock_price * shares
    m["market_cap"] = market_cap

    # ── Valuation ──
    m["pe_ttm"] = _safe_div(stock_price, _safe_div(ttm_net_income, shares)) if shares else None
    m["pb"] = _safe_div(stock_price, _safe_div(total_equity, shares)) if shares else None
    m["ps"] = _safe_div(market_cap, ttm_revenue)

    ev = None
    if market_cap is not None:
        ev = market_cap + short_term_debt + long_term_debt - cash
    m["ev_ebitda"] = _safe_div(ev, ttm_ebitda)
    m["p_fcf"] = _safe_div(market_cap, ttm_fcf)

    # ── Per-Share ──
    latest_net_income = _safe_float(is_latest, "netIncome")
    latest_revenue = _safe_float(is_latest, "totalRevenue")
    latest_opcf = _safe_float(cf_latest, "operatingCashflow")
    latest_capex = _safe_float(cf_latest, "capitalExpenditures")

    m["eps"] = _safe_div(latest_net_income, shares)
    m["revenue_per_share"] = _safe_div(latest_revenue, shares)
    m["book_value_per_share"] = _safe_div(total_equity, shares)
    m["fcf_per_share"] = None
    if latest_opcf is not None and latest_capex is not None and shares:
        fcf = latest_opcf - abs(latest_capex)
        m["fcf_per_share"] = _safe_div(fcf, shares)

    # ── Profitability ──
    gross_profit = _safe_float(is_latest, "grossProfit")
    operating_income = _safe_float(is_latest, "operatingIncome")
    net_income_latest = latest_net_income
    revenue_latest = latest_revenue

    m["gross_margin"] = _safe_div(gross_profit, revenue_latest)
    m["operating_margin"] = _safe_div(operating_income, revenue_latest)
    m["net_margin"] = _safe_div(net_income_latest, revenue_latest)
    m["roe"] = _safe_div(ttm_net_income, total_equity)
    m["roa"] = _safe_div(ttm_net_income, total_assets)

    # ── Financial Health ──
    total_debt = short_term_debt + long_term_debt
    m["debt_to_equity"] = _safe_div(total_debt, total_equity)
    m["current_ratio"] = _safe_div(total_current_assets, total_current_liabilities)
    m["quick_ratio"] = None
    if total_current_assets is not None and total_current_liabilities is not None and total_current_liabilities != 0:
        m["quick_ratio"] = (total_current_assets - inventory) / total_current_liabilities
    m["interest_coverage"] = _safe_div(ttm_ebitda, ttm_interest_expense)
    m["cash_per_share"] = _safe_div(cash, shares)

    # ── Growth (YOY) ──
    m["earnings_growth_yoy"] = _compute_yoy(is_records, "netIncome")
    m["revenue_growth_yoy"] = _compute_yoy(is_records, "totalRevenue")

    # ── Market Data ──
    if curr_date:
        price_derived = _compute_price_derived(ticker or bs.get("symbol", ""), curr_date)
        # 如果 bs 没有 symbol，用外部传入的
        m.update(price_derived)
    else:
        m["52WeekHigh"] = None
        m["52WeekLow"] = None
        m["50DMA"] = None
        m["200DMA"] = None

    # ── Earnings ──
    if earnings_records:
        latest_earning = earnings_records[0]
        m["reported_eps"] = _safe_float(latest_earning, "reportedEPS")
        m["estimated_eps"] = _safe_float(latest_earning, "estimatedEPS")
        m["eps_surprise"] = _safe_float(latest_earning, "surprise")
        m["eps_surprise_pct"] = _safe_float(latest_earning, "surprisePercentage")
        m["earnings_date"] = latest_earning.get("fiscalDateEnding", "N/A")
    else:
        m["reported_eps"] = None
        m["estimated_eps"] = None
        m["eps_surprise"] = None
        m["eps_surprise_pct"] = None
        m["earnings_date"] = "N/A"

    # 报告日期标注
    m["report_date"] = bs.get("fiscalDateEnding", "N/A") if bs else "N/A"

    return m


def _compute_yoy(records: list[dict], field: str):
    """计算同比增长率。需要至少 5 个季度数据。"""
    if len(records) < 5:
        return None
    curr_val = _safe_float(records[0], field)
    prev_val = _safe_float(records[4], field)
    if curr_val is None or prev_val is None or prev_val == 0:
        return None
    return (curr_val - prev_val) / abs(prev_val)


# ---------------------------------------------------------------------------
# 格式化
# ---------------------------------------------------------------------------

def _fmt(value, fmt_type: str = "raw") -> str:
    if value is None:
        return "N/A"
    try:
        if fmt_type == "pct":
            return f"{float(value) * 100:.2f}%"
        elif fmt_type == "ratio":
            return f"{float(value):.2f}"
        elif fmt_type == "currency":
            v = float(value)
            if abs(v) >= 1e12:
                return f"${v/1e12:.2f}T"
            elif abs(v) >= 1e9:
                return f"${v/1e9:.2f}B"
            elif abs(v) >= 1e6:
                return f"${v/1e6:.2f}M"
            else:
                return f"${v:,.2f}"
        elif fmt_type == "per_share":
            return f"${float(value):.2f}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value)


def _format_report(m: dict, ticker: str) -> str:
    lines = []

    lines.append(f"=== Fundamental Analysis for {ticker.upper()} ===")
    lines.append(f"Latest financial data as of: {m.get('report_date', 'N/A')}")
    lines.append("")

    # Valuation
    lines.append("=== Valuation Metrics ===")
    lines.append(f"Market Cap: {_fmt(m.get('market_cap'), 'currency')}")
    lines.append(f"P/E Ratio (TTM): {_fmt(m.get('pe_ttm'), 'ratio')}")
    lines.append(f"Price to Book: {_fmt(m.get('pb'), 'ratio')}")
    lines.append(f"Price to Sales: {_fmt(m.get('ps'), 'ratio')}")
    lines.append(f"EV/EBITDA: {_fmt(m.get('ev_ebitda'), 'ratio')}")
    lines.append(f"Price to Free Cash Flow: {_fmt(m.get('p_fcf'), 'ratio')}")
    lines.append("")

    # Per-Share
    lines.append("=== Per-Share Data ===")
    lines.append(f"EPS (latest quarter): {_fmt(m.get('eps'), 'per_share')}")
    lines.append(f"Revenue per Share: {_fmt(m.get('revenue_per_share'), 'per_share')}")
    lines.append(f"Book Value per Share: {_fmt(m.get('book_value_per_share'), 'per_share')}")
    lines.append(f"Free Cash Flow per Share: {_fmt(m.get('fcf_per_share'), 'per_share')}")
    lines.append("")

    # Profitability
    lines.append("=== Profitability ===")
    lines.append(f"Gross Margin: {_fmt(m.get('gross_margin'), 'pct')}")
    lines.append(f"Operating Margin: {_fmt(m.get('operating_margin'), 'pct')}")
    lines.append(f"Net Margin: {_fmt(m.get('net_margin'), 'pct')}")
    lines.append(f"Return on Equity (ROE): {_fmt(m.get('roe'), 'pct')}")
    lines.append(f"Return on Assets (ROA): {_fmt(m.get('roa'), 'pct')}")
    lines.append("")

    # Financial Health
    lines.append("=== Financial Health ===")
    lines.append(f"Debt to Equity: {_fmt(m.get('debt_to_equity'), 'ratio')}")
    lines.append(f"Current Ratio: {_fmt(m.get('current_ratio'), 'ratio')}")
    lines.append(f"Quick Ratio: {_fmt(m.get('quick_ratio'), 'ratio')}")
    lines.append(f"Interest Coverage: {_fmt(m.get('interest_coverage'), 'ratio')}")
    lines.append(f"Cash per Share: {_fmt(m.get('cash_per_share'), 'per_share')}")
    lines.append("")

    # Growth
    lines.append("=== Growth (YOY) ===")
    lines.append(f"Quarterly Earnings Growth YOY: {_fmt(m.get('earnings_growth_yoy'), 'pct')}")
    lines.append(f"Quarterly Revenue Growth YOY: {_fmt(m.get('revenue_growth_yoy'), 'pct')}")
    lines.append("")

    # Market Data
    lines.append("=== Market Data ===")
    lines.append(f"52-Week High: {_fmt(m.get('52WeekHigh'), 'per_share')}")
    lines.append(f"52-Week Low: {_fmt(m.get('52WeekLow'), 'per_share')}")
    lines.append(f"50-Day Moving Average: {_fmt(m.get('50DMA'), 'per_share')}")
    lines.append(f"200-Day Moving Average: {_fmt(m.get('200DMA'), 'per_share')}")
    lines.append("")

    # Earnings
    lines.append("=== Earnings ===")
    lines.append(f"Fiscal Quarter Ending: {m.get('earnings_date', 'N/A')}")
    lines.append(f"Reported EPS: {_fmt(m.get('reported_eps'), 'per_share')}")
    lines.append(f"Estimated EPS: {_fmt(m.get('estimated_eps'), 'per_share')}")
    lines.append(f"EPS Surprise: {_fmt(m.get('eps_surprise'), 'per_share')}")
    lines.append(f"Surprise %: {_fmt(m.get('eps_surprise_pct'), 'ratio')}%")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主函数
# ---------------------------------------------------------------------------

def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    """使用 Alpha Vantage 获取综合基本面数据。

    从 BALANCE_SHEET、INCOME_STATEMENT、CASH_FLOW、EARNINGS 端点获取数据，
    结合股价计算估值/盈利/偿债指标。

    Args:
        ticker: 股票代码 (e.g., "AAPL")
        curr_date: 交易日期 yyyy-mm-dd，晚于此日期的数据将被排除

    Returns:
        格式化的基本面分析报告文本
    """
    # 获取数据（有缓存时零 API 消耗）
    bs_data = _fetch_and_cache_av(ticker, "BALANCE_SHEET", "balance_sheet")
    is_data = _fetch_and_cache_av(ticker, "INCOME_STATEMENT", "income_statement")
    cf_data = _fetch_and_cache_av(ticker, "CASH_FLOW", "cash_flow")
    earnings_data = _fetch_and_cache_av(ticker, "EARNINGS", "earnings")

    # 按 curr_date 过滤季度数据
    bs_records = _get_quarterly_before(bs_data, curr_date) if curr_date else bs_data.get("quarterlyReports", [])
    is_records = _get_quarterly_before(is_data, curr_date) if curr_date else is_data.get("quarterlyReports", [])
    cf_records = _get_quarterly_before(cf_data, curr_date) if curr_date else cf_data.get("quarterlyReports", [])
    earnings_records = _get_earnings_before(earnings_data, curr_date) if curr_date else earnings_data.get("quarterlyEarnings", [])

    # 获取股价
    stock_price = _get_stock_price(ticker, curr_date) if curr_date else None

    # 计算指标
    metrics = _compute_metrics(bs_records, is_records, cf_records, earnings_records, stock_price, curr_date, ticker=ticker)

    # 格式化报告
    return _format_report(metrics, ticker)
