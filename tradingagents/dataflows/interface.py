from datetime import datetime, timedelta

# Import from vendor-specific modules
from .y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_news as get_alpha_vantage_news,
    get_global_news as get_alpha_vantage_global_news,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
)
from .alpha_vantage_fundamentals_full import get_fundamentals as get_av_fundamentals
from .alpha_vantage_common import AlphaVantageRateLimitError
from .local_cache import load_cache, save_cache
from .bulk_cache import (
    bulk_has, bulk_load, bulk_save, strip_comment_header,
    slice_csv_by_range, slice_csv_before, slice_json_news,
)

# Configuration and routing logic
from .config import get_config

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ]
    },
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_av_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
    },
    "get_global_news": {
        "alpha_vantage": get_alpha_vantage_global_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
    },
}

# ── 批量缓存配置 ────────────────────────────────────────────────────────────

# 使用批量缓存的方法（首次拉取 5 年，后续本地切片）
BULK_CACHE_METHODS = {
    "get_stock_data", "get_indicators",
    "get_balance_sheet", "get_cashflow", "get_income_statement",
    "get_fundamentals",
    "get_insider_transactions",
    "get_news", "get_global_news",
}


def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")


def _call_vendor_with_fallback(method: str, *args, **kwargs):
    """调用 vendor 实现，支持 fallback 链。不涉及任何缓存逻辑。"""
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    all_available_vendors = list(VENDOR_METHODS[method].keys())
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except AlphaVantageRateLimitError:
            continue

    raise RuntimeError(f"No available vendor for '{method}'")


# ── 批量缓存逻辑 ────────────────────────────────────────────────────────────

def _prefetch_range(config: dict) -> tuple[str, str]:
    """计算预拉取的日期范围：[today - prefetch_years, today]。"""
    years = config.get("bulk_cache_prefetch_years", 5)
    today = datetime.now()
    start = today - timedelta(days=years * 365)
    return start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")


def _generate_date_segments(start_date: str, end_date: str, segment_days: int = 5) -> list[tuple[str, str]]:
    """将日期范围分割为等长段，返回 (start, end) 列表。"""
    segments = []
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    current = start_dt
    while current < end_dt:
        seg_end = min(current + timedelta(days=segment_days - 1), end_dt)
        segments.append((current.strftime("%Y-%m-%d"), seg_end.strftime("%Y-%m-%d")))
        current = seg_end + timedelta(days=1)

    return segments


def _segmented_news_fetch(label: str, start_date: str, end_date: str,
                          fetch_fn, segment_days: int = 5,
                          rate_limit_seconds: float = 13.0) -> str | None:
    """分段拉取新闻，合并去重，返回 JSON 字符串。

    Args:
        label: 日志标识（如 ticker 或 "GLOBAL"）
        fetch_fn: callable(seg_start, seg_end) -> raw JSON string/dict
        segment_days: 每段天数
        rate_limit_seconds: 请求间隔秒数
    """
    import json as _json
    import time

    segments = _generate_date_segments(start_date, end_date, segment_days)
    all_articles = []
    seen_urls = set()
    template_data = None
    total = len(segments)

    print(f"[bulk_cache] 开始分段新闻拉取 [{label}]: {total} 段, {start_date} ~ {end_date}")

    for i, (seg_start, seg_end) in enumerate(segments):
        try:
            raw = fetch_fn(seg_start, seg_end)
            if not isinstance(raw, str):
                raw = _json.dumps(raw, ensure_ascii=False)

            data = _json.loads(raw)

            if "Information" in data or "Error" in data:
                print(f"[bulk_cache]   {i+1}/{total} ({seg_start}~{seg_end}): API 错误, 跳过")
                if rate_limit_seconds > 0 and i < total - 1:
                    time.sleep(rate_limit_seconds)
                continue

            if template_data is None:
                template_data = {k: v for k, v in data.items() if k != "feed"}

            feed = data.get("feed", [])
            new_count = 0
            for article in feed:
                url = article.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(article)
                    new_count += 1

            print(f"[bulk_cache]   {i+1}/{total} ({seg_start}~{seg_end}): "
                  f"{len(feed)} 篇, {new_count} 新增 (累计: {len(all_articles)})")

        except Exception as e:
            print(f"[bulk_cache]   {i+1}/{total} ({seg_start}~{seg_end}): 错误: {e}")

        if i < total - 1 and rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)

    if not all_articles:
        return None

    result = template_data or {}
    result["feed"] = all_articles
    result["items"] = str(len(all_articles))

    print(f"[bulk_cache] [{label}] 拉取完成: {len(all_articles)} 篇")

    return _json.dumps(result, ensure_ascii=False)


def _try_bulk_cache(method: str, args: tuple, kwargs: dict, config: dict):
    """尝试从批量缓存获取数据。成功返回结果字符串，失败返回 None。"""
    try:
        if method == "get_stock_data":
            return _bulk_stock_data(args, kwargs, config)
        elif method == "get_indicators":
            return _bulk_indicators(args, kwargs, config)
        elif method == "get_balance_sheet":
            return _bulk_balance_sheet(args, kwargs, config)
        elif method == "get_cashflow":
            return _bulk_cashflow(args, kwargs, config)
        elif method == "get_income_statement":
            return _bulk_income_statement(args, kwargs, config)
        elif method == "get_insider_transactions":
            return _bulk_insider_transactions(args, kwargs, config)
        elif method == "get_news":
            return _bulk_news(args, kwargs, config)
        elif method == "get_global_news":
            return _bulk_global_news(args, kwargs, config)
        elif method == "get_fundamentals":
            return _bulk_fundamentals(args, kwargs, config)
    except Exception as e:
        print(f"[bulk_cache] {method} 失败，降级到旧逻辑: {e}")
        return None
    return None


def _bulk_stock_data(args, kwargs, config):
    """get_stock_data(symbol, start_date, end_date)"""
    ticker = args[0]
    start_date, end_date = args[1], args[2]
    data_type = "stock_data"

    if not bulk_has(ticker, data_type):
        pf_start, pf_end = _prefetch_range(config)
        raw = _call_vendor_with_fallback("get_stock_data", ticker, pf_start, pf_end)
        csv_data = strip_comment_header(raw)
        if "timestamp" not in csv_data.split("\n", 1)[0]:
            print(f"[bulk_cache] stock_data {ticker}: AV 返回异常，不缓存")
            return None
        bulk_save(ticker, data_type, csv_data, {"start_date": pf_start, "end_date": pf_end})

    full_csv = bulk_load(ticker, data_type)
    sliced = slice_csv_by_range(full_csv, start_date, end_date)

    # 重建注释头
    row_count = max(sliced.strip().count("\n"), 0)  # 减去列头行
    header = (
        f"# Stock data for {ticker.upper()} from {start_date} to {end_date}\n"
        f"# Total records: {row_count}\n"
        f"# Data from bulk cache\n\n"
    )
    return header + sliced


def _bulk_indicators(args, kwargs, config):
    """get_indicators(symbol, indicator, curr_date, look_back_days)

    直接调用 AV API 获取原始 CSV，绕过 get_indicator() 的格式化逻辑。
    MACD 三指标共享同一 API 调用结果，BBANDS 三指标同理。
    """
    from .alpha_vantage_common import _make_api_request

    ticker = args[0]
    indicator = args[1]
    curr_date = args[2]
    look_back_days = args[3] if len(args) > 3 else kwargs.get("look_back_days", 30)

    # yfinance 路径已有自己的 bulk 机制，这里只处理 alpha_vantage
    category = get_category_for_method("get_indicators")
    vendor_name = get_vendor(category, "get_indicators")
    if "yfinance" in vendor_name:
        return None  # 降级，让 yfinance 走自己的逻辑

    # VWMA 不被 AV 支持，直接降级
    if indicator == "vwma":
        return None

    # ── 指标 → AV API 映射 ──────────────────────────────────────────────────
    # group_key: 共享同一 API 调用的指标组（MACD×3, BBANDS×3）
    # av_func / av_params: AV API 函数名和参数
    # col_name: 从 CSV 中提取的列名
    _INDICATOR_MAP = {
        "close_50_sma":  {"group": "sma_50",  "av_func": "SMA",   "av_params": {"time_period": "50",  "series_type": "close"}, "col": "SMA"},
        "close_200_sma": {"group": "sma_200", "av_func": "SMA",   "av_params": {"time_period": "200", "series_type": "close"}, "col": "SMA"},
        "close_10_ema":  {"group": "ema_10",  "av_func": "EMA",   "av_params": {"time_period": "10",  "series_type": "close"}, "col": "EMA"},
        "macd":          {"group": "macd",    "av_func": "MACDEXT",  "av_params": {"series_type": "close"}, "col": "MACD"},
        "macds":         {"group": "macd",    "av_func": "MACDEXT",  "av_params": {"series_type": "close"}, "col": "MACD_Signal"},
        "macdh":         {"group": "macd",    "av_func": "MACDEXT",  "av_params": {"series_type": "close"}, "col": "MACD_Hist"},
        "rsi":           {"group": "rsi",     "av_func": "RSI",   "av_params": {"time_period": "14",  "series_type": "close"}, "col": "RSI"},
        "boll":          {"group": "bbands",  "av_func": "BBANDS","av_params": {"time_period": "20",  "series_type": "close"}, "col": "Real Middle Band"},
        "boll_ub":       {"group": "bbands",  "av_func": "BBANDS","av_params": {"time_period": "20",  "series_type": "close"}, "col": "Real Upper Band"},
        "boll_lb":       {"group": "bbands",  "av_func": "BBANDS","av_params": {"time_period": "20",  "series_type": "close"}, "col": "Real Lower Band"},
        "atr":           {"group": "atr",     "av_func": "ATR",   "av_params": {"time_period": "14"}, "col": "ATR"},
    }

    _INDICATOR_DESCRIPTIONS = {
        "close_50_sma": "50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.",
        "close_200_sma": "200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.",
        "close_10_ema": "10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.",
        "macd": "MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.",
        "macds": "MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.",
        "macdh": "MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.",
        "rsi": "RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.",
        "boll": "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.",
        "boll_ub": "Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.",
        "boll_lb": "Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.",
        "atr": "ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.",
    }

    if indicator not in _INDICATOR_MAP:
        return None  # 不支持的指标，降级

    spec = _INDICATOR_MAP[indicator]
    group_key = spec["group"]
    data_type = f"indicator_raw_{group_key}"

    # ── 1. 拉取并缓存原始 CSV（按 group 共享） ─────────────────────────────
    if not bulk_has(ticker, data_type):
        params = {"symbol": ticker, "interval": "daily", "datatype": "csv"}
        params.update(spec["av_params"])
        raw_csv = _make_api_request(spec["av_func"], params)

        # 简单校验：应包含 "time" 列头
        if "time" not in raw_csv.split("\n", 1)[0]:
            print(f"[bulk_cache] indicator {indicator}: AV 返回异常，不缓存")
            return None  # 降级

        pf_start, pf_end = _prefetch_range(config)
        bulk_save(ticker, data_type, raw_csv, {"start_date": pf_start, "end_date": pf_end})

    # ── 2. 读取、切片 ──────────────────────────────────────────────────────
    full_csv = bulk_load(ticker, data_type)

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_dt - timedelta(days=int(look_back_days))
    sliced_csv = slice_csv_by_range(full_csv, before.strftime("%Y-%m-%d"), curr_date)

    # ── 3. 提取目标列，格式化为 date: value 文本 ───────────────────────────
    target_col = spec["col"]
    lines = sliced_csv.strip().split("\n")
    if len(lines) < 2:
        return f"## {indicator.upper()} values: No data available for the specified date range.\n\n{_INDICATOR_DESCRIPTIONS.get(indicator, '')}"

    header = [c.strip() for c in lines[0].split(",")]
    try:
        date_idx = header.index("time")
    except ValueError:
        date_idx = 0
    try:
        val_idx = header.index(target_col)
    except ValueError:
        val_idx = 1  # fallback

    data_lines = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.split(",")
        if len(cols) > max(date_idx, val_idx):
            data_lines.append(f"{cols[date_idx].strip()}: {cols[val_idx].strip()}")

    # 按日期排序（AV CSV 默认降序，需要升序）
    data_lines.sort()

    ind_string = "\n".join(data_lines) if data_lines else "No data available for the specified date range."

    return (
        f"## {indicator.upper()} values from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + ind_string
        + "\n\n"
        + _INDICATOR_DESCRIPTIONS.get(indicator, "")
    )


def _bulk_balance_sheet(args, kwargs, config):
    """get_balance_sheet(ticker, freq, curr_date)"""
    ticker = args[0]
    freq = args[1] if len(args) > 1 else kwargs.get("freq", "quarterly")
    curr_date = args[2] if len(args) > 2 else kwargs.get("curr_date")
    data_type = f"balance_sheet_{freq}"

    if not bulk_has(ticker, data_type):
        # 不传 curr_date，拉取全量
        raw = _call_vendor_with_fallback("get_balance_sheet", ticker, freq)
        csv_data = strip_comment_header(raw)
        if "fiscalDateEnding" not in csv_data.split("\n", 1)[0]:
            print(f"[bulk_cache] {data_type} {ticker}: AV 返回异常，不缓存")
            return None
        bulk_save(ticker, data_type, csv_data, {"ticker": ticker, "freq": freq})

    full_csv = bulk_load(ticker, data_type)
    if curr_date:
        return slice_csv_before(full_csv, curr_date)
    return full_csv


def _bulk_cashflow(args, kwargs, config):
    """get_cashflow(ticker, freq, curr_date)"""
    ticker = args[0]
    freq = args[1] if len(args) > 1 else kwargs.get("freq", "quarterly")
    curr_date = args[2] if len(args) > 2 else kwargs.get("curr_date")
    data_type = f"cashflow_{freq}"

    if not bulk_has(ticker, data_type):
        raw = _call_vendor_with_fallback("get_cashflow", ticker, freq)
        csv_data = strip_comment_header(raw)
        if "fiscalDateEnding" not in csv_data.split("\n", 1)[0]:
            print(f"[bulk_cache] {data_type} {ticker}: AV 返回异常，不缓存")
            return None
        bulk_save(ticker, data_type, csv_data, {"ticker": ticker, "freq": freq})

    full_csv = bulk_load(ticker, data_type)
    if curr_date:
        return slice_csv_before(full_csv, curr_date)
    return full_csv


def _bulk_income_statement(args, kwargs, config):
    """get_income_statement(ticker, freq, curr_date)"""
    ticker = args[0]
    freq = args[1] if len(args) > 1 else kwargs.get("freq", "quarterly")
    curr_date = args[2] if len(args) > 2 else kwargs.get("curr_date")
    data_type = f"income_statement_{freq}"

    if not bulk_has(ticker, data_type):
        raw = _call_vendor_with_fallback("get_income_statement", ticker, freq)
        csv_data = strip_comment_header(raw)
        if "fiscalDateEnding" not in csv_data.split("\n", 1)[0]:
            print(f"[bulk_cache] {data_type} {ticker}: AV 返回异常，不缓存")
            return None
        bulk_save(ticker, data_type, csv_data, {"ticker": ticker, "freq": freq})

    full_csv = bulk_load(ticker, data_type)
    if curr_date:
        return slice_csv_before(full_csv, curr_date)
    return full_csv


def _bulk_insider_transactions(args, kwargs, config):
    """get_insider_transactions(ticker, curr_date)

    直接调用 AV INSIDER_TRANSACTIONS API，解析 JSON 转 CSV 存储。
    AV 返回 6000+ 条记录（覆盖 20+ 年），远超 yfinance 的 20 条。
    """
    import json as _json
    import pandas as pd
    from .alpha_vantage_common import _make_api_request

    ticker = args[0]
    curr_date = args[1] if len(args) > 1 else kwargs.get("curr_date")
    data_type = "insider_transactions"

    if not bulk_has(ticker, data_type):
        try:
            raw = _make_api_request("INSIDER_TRANSACTIONS", {"symbol": ticker})
            data = _json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            print(f"[bulk_cache] insider_transactions AV 请求失败: {e}")
            return None  # 降级

        records = data.get("data", [])
        if not records:
            return None

        df = pd.DataFrame(records)
        # 确保 transaction_date 为第一列（供 slice_csv_before 识别）
        if "transaction_date" in df.columns:
            cols = ["transaction_date"] + [c for c in df.columns if c != "transaction_date"]
            df = df[cols]

        csv_data = df.to_csv(index=False)
        bulk_save(ticker, data_type, csv_data, {"ticker": ticker})

    full_csv = bulk_load(ticker, data_type)
    if curr_date:
        sliced = slice_csv_before(full_csv, curr_date, date_col="transaction_date")
    else:
        sliced = full_csv

    # 只返回最近 50 条，避免撑爆 LLM 上下文
    lines = sliced.strip().split("\n")
    if len(lines) > 51:  # 1 header + 50 data rows
        sliced = "\n".join(lines[:51])
    return sliced


def _bulk_fundamentals(args, kwargs, config):
    """get_fundamentals(ticker, curr_date)

    直接调用 vendor（内部从 bulk/{TICKER}/*.json 读取），跳过按请求缓存。
    """
    ticker = args[0]
    curr_date = args[1] if len(args) > 1 else kwargs.get("curr_date")
    return get_av_fundamentals(ticker, curr_date)


def _is_valid_news_response(raw: str) -> bool:
    """检查 AV 新闻 API 响应是否有效（非错误、非空 feed）。"""
    try:
        import json
        data = json.loads(raw) if isinstance(raw, str) else raw
        if "Information" in data or "Error" in data:
            return False
        feed = data.get("feed", [])
        return len(feed) > 0
    except (json.JSONDecodeError, TypeError):
        return False


def _bulk_news(args, kwargs, config):
    """get_news(ticker, start_date, end_date)

    分段预拉取：5 天一段覆盖 5 年，每段 limit=1000，合并去重后存入缓存。
    首次拉取约 79 分钟（365 段 × 13 秒），后续查询从缓存切片，零 API。
    """
    ticker = args[0]
    start_date, end_date = args[1], args[2]
    data_type = "news"

    if not bulk_has(ticker, data_type, ext=".txt"):
        pf_start, pf_end = _prefetch_range(config)

        def fetch_fn(seg_start, seg_end):
            return get_alpha_vantage_news(
                ticker, seg_start, seg_end, limit=1000, sort="LATEST"
            )

        merged_json = _segmented_news_fetch(
            ticker, pf_start, pf_end,
            fetch_fn, segment_days=5, rate_limit_seconds=1.0
        )

        if merged_json and _is_valid_news_response(merged_json):
            bulk_save(ticker, data_type, merged_json,
                      {"start_date": pf_start, "end_date": pf_end}, ext=".txt")
        else:
            return None

    full_json = bulk_load(ticker, data_type, ext=".txt")
    sliced = slice_json_news(full_json, start_date, end_date, limit=100)

    try:
        import json
        data = json.loads(sliced)
        if len(data.get("feed", [])) == 0:
            return None
    except (json.JSONDecodeError, TypeError):
        pass

    return sliced


def _bulk_global_news(args, kwargs, config):
    """get_global_news(curr_date, look_back_days, limit)

    分段预拉取：30 天一段覆盖 5 年（全局新闻约 26 篇/天，30 天 ≈ 780 篇 < 1000 上限）。
    首次拉取约 13 分钟（61 段 × 13 秒），后续查询从缓存切片。
    """
    curr_date = args[0]
    look_back_days = args[1] if len(args) > 1 else kwargs.get("look_back_days", 7)
    limit = args[2] if len(args) > 2 else kwargs.get("limit", 5)
    ticker = "_GLOBAL"
    data_type = "global_news"

    if not bulk_has(ticker, data_type, ext=".txt"):
        pf_start, pf_end = _prefetch_range(config)

        def fetch_fn(seg_start, seg_end):
            seg_days = (datetime.strptime(seg_end, "%Y-%m-%d") -
                        datetime.strptime(seg_start, "%Y-%m-%d")).days + 1
            return get_alpha_vantage_global_news(
                seg_end, look_back_days=seg_days, limit=1000, sort="LATEST"
            )

        merged_json = _segmented_news_fetch(
            "GLOBAL", pf_start, pf_end,
            fetch_fn, segment_days=15, rate_limit_seconds=1.0
        )

        if merged_json and _is_valid_news_response(merged_json):
            bulk_save(ticker, data_type, merged_json,
                      {"start_date": pf_start, "end_date": pf_end}, ext=".txt")
        else:
            return None

    full_json = bulk_load(ticker, data_type, ext=".txt")

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - timedelta(days=int(look_back_days))
    sliced = slice_json_news(full_json, start_dt.strftime("%Y-%m-%d"), curr_date, limit=int(limit))

    try:
        import json
        data = json.loads(sliced)
        if len(data.get("feed", [])) == 0:
            return None
    except (json.JSONDecodeError, TypeError):
        pass

    return sliced


# ── 主路由 ──────────────────────────────────────────────────────────────────

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation.
    优先级：批量缓存 → 按请求缓存 → 调用 vendor API。
    """
    config = get_config()

    # 1. 批量缓存方法 — 不降级，返回 None 即表示数据不可用
    if config.get("bulk_cache_enabled", True) and method in BULK_CACHE_METHODS:
        return _try_bulk_cache(method, args, kwargs, config)

    # 2. 非批量方法：按请求缓存 → 调用 vendor
    cached = load_cache(method, args, kwargs)
    if cached is not None:
        return cached

    result = _call_vendor_with_fallback(method, *args, **kwargs)
    save_cache(method, args, kwargs, result)
    return result
