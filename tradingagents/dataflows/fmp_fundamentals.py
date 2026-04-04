import os
import json
from io import StringIO
from datetime import datetime, timedelta

import pandas as pd

from .fmp_common import fmp_api_request
from .config import get_config


def _get_cache_dir() -> str:
    """Get the FMP cache directory path, creating it if needed."""
    config = get_config()
    project_dir = config.get("project_dir", ".")
    cache_dir = os.path.join(project_dir, "dataflows", "fmp_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _fetch_and_cache(ticker: str, endpoint: str, params: dict = None) -> list | dict:
    """Fetch data from FMP and cache locally. Return cached data if available.

    Args:
        ticker: Stock ticker symbol
        endpoint: FMP endpoint name (e.g., "key-metrics")
        params: Optional extra query parameters

    Returns:
        Parsed JSON data (list of dicts for time-series, dict/list for profile)
    """
    cache_dir = _get_cache_dir()
    safe_endpoint = endpoint.replace("/", "_")
    cache_file = os.path.join(cache_dir, f"{ticker}_{safe_endpoint}.json")

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    request_params = params.copy() if params else {}
    data = fmp_api_request(f"/{endpoint}/{ticker}", request_params)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


def _get_latest_before(records: list[dict], curr_date: str, date_field: str = "date") -> dict | None:
    """Get the most recent record with date <= curr_date.

    Args:
        records: List of dicts, each containing a date field
        curr_date: Cutoff date in yyyy-mm-dd format
        date_field: Name of the date field in records

    Returns:
        The most recent record before curr_date, or None
    """
    if not records or not curr_date:
        return records[0] if records else None

    cutoff = datetime.strptime(curr_date, "%Y-%m-%d")
    candidates = []
    for r in records:
        date_str = r.get(date_field, "")
        if not date_str:
            continue
        try:
            # FMP dates can be "yyyy-mm-dd" or "yyyy-mm-dd HH:MM:SS"
            record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if record_date <= cutoff:
                candidates.append((record_date, r))
        except (ValueError, TypeError):
            continue

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _get_all_before(records: list[dict], curr_date: str, date_field: str = "date", limit: int = 5) -> list[dict]:
    """Get all records with date <= curr_date, up to limit.

    Args:
        records: List of dicts, each containing a date field
        curr_date: Cutoff date in yyyy-mm-dd format
        date_field: Name of the date field in records
        limit: Maximum number of records to return

    Returns:
        List of records, most recent first
    """
    if not records or not curr_date:
        return records[:limit] if records else []

    cutoff = datetime.strptime(curr_date, "%Y-%m-%d")
    candidates = []
    for r in records:
        date_str = r.get(date_field, "")
        if not date_str:
            continue
        try:
            record_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            if record_date <= cutoff:
                candidates.append((record_date, r))
        except (ValueError, TypeError):
            continue

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates[:limit]]


def _fmt(value, fmt_type: str = "raw") -> str:
    """Format a value for display in the report."""
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


def _compute_yoy_growth(records: list[dict], curr_date: str, value_field: str) -> float | None:
    """Compute YOY growth by comparing the latest quarter to the same quarter one year ago.

    Args:
        records: List of quarterly records sorted by date (newest first from FMP)
        curr_date: Cutoff date
        value_field: Field name to compare (e.g., "netIncomePerShare", "revenuePerShare")

    Returns:
        YOY growth as a decimal (e.g., 0.15 for 15%), or None if not computable
    """
    filtered = _get_all_before(records, curr_date, limit=8)  # ~2 years of quarters
    if len(filtered) < 5:
        return None

    latest = filtered[0]
    # Find the record ~4 quarters ago (same quarter last year)
    yoy_record = filtered[4] if len(filtered) > 4 else None
    if not yoy_record:
        return None

    try:
        curr_val = float(latest.get(value_field, 0))
        prev_val = float(yoy_record.get(value_field, 0))
        if prev_val == 0:
            return None
        return (curr_val - prev_val) / abs(prev_val)
    except (ValueError, TypeError):
        return None


def _compute_price_derived(ticker: str, curr_date: str) -> dict:
    """Compute price-derived metrics: 52WeekHigh/Low, 50DMA, 200DMA.

    Uses route_to_vendor (lazy import to avoid circular dependency) to fetch
    historical price data, then computes the metrics.

    Returns:
        Dict with keys: 52WeekHigh, 52WeekLow, 50DMA, 200DMA (values may be None)
    """
    result = {"52WeekHigh": None, "52WeekLow": None, "50DMA": None, "200DMA": None}

    try:
        # Lazy import to avoid circular dependency (interface imports fmp_fundamentals)
        from .interface import route_to_vendor

        end_date = curr_date
        # Need ~1 year of data for 52-week and 200DMA
        start_dt = datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=370)
        start_date = start_dt.strftime("%Y-%m-%d")

        csv_data = route_to_vendor("get_stock_data", ticker, start_date, end_date)
        if not csv_data or not csv_data.strip():
            return result

        df = pd.read_csv(StringIO(csv_data))
        # Identify the close column (different vendors use different names)
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

        # 52-week high/low (all available data, up to ~1 year)
        result["52WeekHigh"] = round(float(closes.max()), 2)
        result["52WeekLow"] = round(float(closes.min()), 2)

        # 50-day and 200-day moving averages (most recent N rows)
        if len(closes) >= 50:
            result["50DMA"] = round(float(closes.head(50).mean()), 2)
        if len(closes) >= 200:
            result["200DMA"] = round(float(closes.head(200).mean()), 2)

    except Exception:
        pass  # Price-derived fields are best-effort, don't fail the whole report

    return result


def _compute_forward_pe(metrics: dict | None, estimates: dict | None) -> float | None:
    """Compute Forward P/E = Market Cap per Share / Estimated EPS."""
    if not metrics or not estimates:
        return None
    try:
        market_cap = float(metrics.get("marketCap", 0))
        pe_ratio = float(metrics.get("peRatio", 0))
        if pe_ratio == 0:
            return None
        # Derive current price from marketCap / (marketCap / peRatio * EPS-implied shares)
        eps_current = float(metrics.get("netIncomePerShare", 0))
        if eps_current == 0:
            return None
        price = pe_ratio * eps_current

        estimated_eps = float(estimates.get("estimatedEpsAvg", 0))
        if estimated_eps == 0:
            return None
        return round(price / estimated_eps, 2)
    except (ValueError, TypeError):
        return None


def _format_fundamentals_report(
    profile: dict | list,
    metrics: dict | None,
    ratios: dict | None,
    estimates: dict | None,
    grades: list[dict],
    derived: dict | None = None,
) -> str:
    """Format all fundamental data into a structured text report.

    Args:
        profile: Company profile data (dict or list with one dict)
        metrics: Latest key metrics record
        ratios: Latest financial ratios record
        estimates: Latest analyst estimates record
        grades: Recent analyst grade changes
        derived: Computed fields (YOY growth, Forward PE, price-derived metrics)

    Returns:
        Formatted text report string
    """
    # Profile may be a list with one element
    if isinstance(profile, list):
        profile = profile[0] if profile else {}

    metrics = metrics or {}
    ratios = ratios or {}
    estimates = estimates or {}
    derived = derived or {}

    lines = []

    # === Company Profile ===
    lines.append("=== Company Profile ===")
    lines.append(f"Name: {profile.get('companyName', 'N/A')}")
    lines.append(f"Sector: {profile.get('sector', 'N/A')}")
    lines.append(f"Industry: {profile.get('industry', 'N/A')}")
    lines.append(f"Exchange: {profile.get('exchangeShortName', 'N/A')}")
    lines.append(f"Description: {profile.get('description', 'N/A')[:200]}")
    lines.append("")

    # === Valuation Metrics ===
    date_label = metrics.get("date", "N/A")
    lines.append(f"=== Valuation Metrics (as of {date_label}) ===")
    lines.append(f"Market Cap: {_fmt(metrics.get('marketCap'), 'currency')}")
    lines.append(f"Enterprise Value: {_fmt(metrics.get('enterpriseValue'), 'currency')}")
    lines.append(f"P/E Ratio (TTM): {_fmt(metrics.get('peRatio'), 'ratio')}")
    lines.append(f"Forward P/E: {_fmt(derived.get('forwardPE'), 'ratio')}")
    lines.append(f"PEG Ratio: {_fmt(metrics.get('pegRatio'), 'ratio')}")
    lines.append(f"Price to Book: {_fmt(metrics.get('pbRatio'), 'ratio')}")
    lines.append(f"Price to Sales: {_fmt(metrics.get('priceToSalesRatio'), 'ratio')}")
    lines.append(f"EV/Revenue: {_fmt(metrics.get('evToSales'), 'ratio')}")
    lines.append(f"EV/EBITDA: {_fmt(ratios.get('enterpriseValueMultiple'), 'ratio')}")
    lines.append(f"Price to Free Cash Flow: {_fmt(metrics.get('pfcfRatio'), 'ratio')}")
    lines.append("")

    # === Per-Share Data ===
    lines.append("=== Per-Share Data ===")
    lines.append(f"EPS: {_fmt(metrics.get('netIncomePerShare'), 'per_share')}")
    lines.append(f"Revenue per Share: {_fmt(metrics.get('revenuePerShare'), 'per_share')}")
    lines.append(f"Book Value per Share: {_fmt(metrics.get('bookValuePerShare'), 'per_share')}")
    lines.append(f"Tangible Book Value per Share: {_fmt(metrics.get('tangibleBookValuePerShare'), 'per_share')}")
    lines.append(f"Free Cash Flow per Share: {_fmt(metrics.get('freeCashFlowPerShare'), 'per_share')}")
    lines.append(f"Dividend per Share: {_fmt(metrics.get('dividendYield'), 'pct')} (yield)")
    lines.append("")

    # === Profitability ===
    lines.append("=== Profitability ===")
    lines.append(f"Gross Margin: {_fmt(ratios.get('grossProfitMargin'), 'pct')}")
    lines.append(f"Operating Margin: {_fmt(ratios.get('operatingProfitMargin'), 'pct')}")
    lines.append(f"Profit Margin (Net): {_fmt(ratios.get('netProfitMargin'), 'pct')}")
    lines.append(f"Return on Equity (ROE): {_fmt(metrics.get('roe'), 'pct')}")
    lines.append(f"Return on Assets (ROA): {_fmt(ratios.get('returnOnAssets'), 'pct')}")
    lines.append(f"Return on Capital Employed (ROCE): {_fmt(metrics.get('roic'), 'pct')}")
    lines.append("")

    # === Financial Health ===
    lines.append("=== Financial Health ===")
    lines.append(f"Debt to Equity: {_fmt(ratios.get('debtEquityRatio'), 'ratio')}")
    lines.append(f"Debt to Assets: {_fmt(ratios.get('debtRatio'), 'ratio')}")
    lines.append(f"Current Ratio: {_fmt(ratios.get('currentRatio'), 'ratio')}")
    lines.append(f"Quick Ratio: {_fmt(ratios.get('quickRatio'), 'ratio')}")
    lines.append(f"Interest Coverage: {_fmt(ratios.get('interestCoverage'), 'ratio')}")
    lines.append(f"Cash per Share: {_fmt(metrics.get('cashPerShare'), 'per_share')}")
    lines.append("")

    # === Dividends ===
    lines.append("=== Dividends ===")
    lines.append(f"Dividend Yield: {_fmt(metrics.get('dividendYield'), 'pct')}")
    lines.append(f"Payout Ratio: {_fmt(ratios.get('payoutRatio'), 'pct')}")
    lines.append("")

    # === Growth ===
    lines.append("=== Growth (YOY) ===")
    lines.append(f"Quarterly Earnings Growth YOY: {_fmt(derived.get('earningsGrowthYOY'), 'pct')}")
    lines.append(f"Quarterly Revenue Growth YOY: {_fmt(derived.get('revenueGrowthYOY'), 'pct')}")
    lines.append("")

    # === Market Data ===
    lines.append("=== Market Data ===")
    lines.append(f"Beta: {profile.get('beta', 'N/A')}")
    lines.append(f"52-Week High: {_fmt(derived.get('52WeekHigh'), 'per_share')}")
    lines.append(f"52-Week Low: {_fmt(derived.get('52WeekLow'), 'per_share')}")
    lines.append(f"50-Day Moving Average: {_fmt(derived.get('50DMA'), 'per_share')}")
    lines.append(f"200-Day Moving Average: {_fmt(derived.get('200DMA'), 'per_share')}")
    lines.append("")

    # === Analyst Estimates ===
    lines.append("=== Analyst Estimates ===")
    if estimates:
        lines.append(f"Date: {estimates.get('date', 'N/A')}")
        lines.append(f"Estimated EPS (avg): {_fmt(estimates.get('estimatedEpsAvg'), 'per_share')}")
        lines.append(f"Estimated EPS (high): {_fmt(estimates.get('estimatedEpsHigh'), 'per_share')}")
        lines.append(f"Estimated EPS (low): {_fmt(estimates.get('estimatedEpsLow'), 'per_share')}")
        lines.append(f"Estimated Revenue (avg): {_fmt(estimates.get('estimatedRevenueAvg'), 'currency')}")
        lines.append(f"Number of Analysts (EPS): {estimates.get('numberAnalystEstimatedEps', 'N/A')}")
        lines.append(f"Number of Analysts (Revenue): {estimates.get('numberAnalystsEstimatedRevenue', 'N/A')}")
    else:
        lines.append("No analyst estimates available for this period.")
    lines.append("")

    # === Recent Analyst Ratings ===
    lines.append("=== Recent Analyst Ratings ===")
    if grades:
        for g in grades:
            date = g.get("date", "N/A")[:10]
            company = g.get("gradingCompany", "N/A")
            prev = g.get("previousGrade", "N/A")
            new = g.get("newGrade", "N/A")
            action = g.get("action", "")
            lines.append(f"  - {date}: {company} {action} {prev} -> {new}")
    else:
        lines.append("No recent analyst rating changes available.")
    lines.append("")

    return "\n".join(lines)


def get_fundamentals(ticker: str, curr_date: str = None) -> str:
    """Retrieve comprehensive fundamental data for a ticker using FMP.

    Fetches data from multiple FMP endpoints, caches locally, and filters
    by curr_date to return only data available at that point in time.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        curr_date: Trading date in yyyy-mm-dd format. Data after this date
                   is excluded to prevent backtesting data leakage.

    Returns:
        Formatted text report with company fundamentals
    """
    # Fetch (or read from cache) all data sources
    key_metrics = _fetch_and_cache(ticker, "key-metrics", {"period": "quarter"})
    ratios_data = _fetch_and_cache(ticker, "ratios", {"period": "quarter"})
    estimates = _fetch_and_cache(ticker, "analyst-estimates")
    grades = _fetch_and_cache(ticker, "grade")
    profile = _fetch_and_cache(ticker, "profile")

    # Filter by curr_date
    latest_metrics = _get_latest_before(key_metrics, curr_date)
    latest_ratios = _get_latest_before(ratios_data, curr_date)
    latest_estimates = _get_latest_before(estimates, curr_date)
    recent_grades = _get_all_before(grades, curr_date, limit=5)

    # Compute derived fields
    derived = {}
    derived["earningsGrowthYOY"] = _compute_yoy_growth(key_metrics, curr_date, "netIncomePerShare")
    derived["revenueGrowthYOY"] = _compute_yoy_growth(key_metrics, curr_date, "revenuePerShare")
    derived["forwardPE"] = _compute_forward_pe(latest_metrics, latest_estimates)
    if curr_date:
        derived.update(_compute_price_derived(ticker, curr_date))

    return _format_fundamentals_report(
        profile, latest_metrics, latest_ratios, latest_estimates, recent_grades, derived
    )
