"""
FRED（Federal Reserve Economic Data）宏观经济指标模块
- 免费，需注册 API Key（https://fred.stlouisfed.org/docs/api/api_key.html）
- 覆盖：利率、CPI、失业率、GDP、非农就业等核心宏观指标
- 分工说明：本模块只做数据采集与格式化，不做向量化（向量化归 #3）
- #3 向量库可直接调用 get_macro_indicator() 获取历史序列后进行向量化

依赖：pip install fredapi pandas
FRED_API_KEY 通过环境变量 FRED_API_KEY 注入（在 .env 中配置）
"""

from typing import Annotated
from datetime import datetime, timedelta
import os
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# 核心宏观指标代码表（FRED Series ID）
# ─────────────────────────────────────────────────────────────────────────────
MACRO_SERIES = {
    # 利率
    "FEDFUNDS": "Fed Funds Rate (Monthly %)",
    "DFF": "Fed Funds Rate (Daily %)",
    "GS10": "10-Year Treasury Yield (%)",
    "GS2": "2-Year Treasury Yield (%)",
    "T10Y2Y": "10Y-2Y Treasury Spread (%)",
    # 通胀
    "CPIAUCSL": "CPI All Items (YoY %)",
    "CPILFESL": "Core CPI ex Food & Energy (YoY %)",
    "PCEPI": "PCE Price Index",
    # 就业
    "UNRATE": "Unemployment Rate (%)",
    "PAYEMS": "Nonfarm Payrolls (thousands)",
    "ICSA": "Initial Jobless Claims (weekly)",
    # 经济活动
    "GDP": "Real GDP (Quarterly, Billions USD)",
    "INDPRO": "Industrial Production Index",
    "RSXFS": "Retail Sales ex Food Services",
    # 市场情绪/流动性
    "VIXCLS": "CBOE VIX Volatility Index",
    "M2SL": "M2 Money Supply (Billions USD)",
    "DEXUSEU": "USD/EUR Exchange Rate",
    "DEXCHUS": "USD/CNY Exchange Rate",
}

# 友好名称 -> FRED Series ID 的反查表（方便用自然语言查询）
_NAME_TO_ID = {v.split("(")[0].strip().lower(): k for k, v in MACRO_SERIES.items()}
_NAME_TO_ID.update({k.lower(): k for k in MACRO_SERIES})  # 直接用 series id 也可以


def _get_fred_client():
    """获取 FRED API 客户端，API Key 从环境变量读取。"""
    try:
        from fredapi import Fred
    except ImportError:
        raise ImportError(
            "fredapi 未安装，请运行: pip install fredapi\n"
            "同时在 .env 中配置: FRED_API_KEY=your_key_here\n"
            "申请 Key（免费）：https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError(
            "未找到 FRED_API_KEY 环境变量。\n"
            "请在 .env 中添加: FRED_API_KEY=your_key\n"
            "免费申请：https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return Fred(api_key=api_key)


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数（供 interface.py 注册为 Agent 可调用工具）
# ─────────────────────────────────────────────────────────────────────────────

def get_macro_indicator(
    series_id: Annotated[
        str,
        "FRED series ID or indicator name, e.g. 'FEDFUNDS', 'CPIAUCSL', 'UNRATE', 'VIXCLS'",
    ],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    获取 FRED 宏观经济指标历史序列。
    同时写入本地缓存（parquet），供 #3 RAP 向量库直接读取，无需重复采集。
    """
    # 尝试将自然语言名称解析为 series_id
    resolved = series_id.upper().strip()
    if resolved not in MACRO_SERIES:
        fallback = _NAME_TO_ID.get(series_id.lower().strip())
        if fallback:
            resolved = fallback
        # 若还是找不到，大胆尝试直接请求，FRED 会返回错误

    try:
        fred = _get_fred_client()
        series = fred.get_series(
            resolved,
            observation_start=start_date,
            observation_end=end_date,
            # realtime_start prevents using data not yet published on end_date
            # (FRED publication lag can be days to weeks for macro series)
            realtime_start=end_date,
            realtime_end=end_date,
        )
        if series.empty:
            return f"No data found for FRED series '{resolved}' between {start_date} and {end_date}"

        df = series.reset_index()
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["series_id"] = resolved
        df["description"] = MACRO_SERIES.get(resolved, resolved)
        df = df.dropna(subset=["value"]).reset_index(drop=True)

        # 写入本地缓存（#3 直接读取，不重复采集）
        _save_to_cache(df[["date", "value"]], resolved, "macro", start_date, end_date)

        csv_str = df[["date", "value"]].to_csv(index=False)
        desc = MACRO_SERIES.get(resolved, resolved)
        header = (
            f"# FRED Macro Indicator: {resolved}\n"
            f"# Description: {desc}\n"
            f"# Date range: {start_date} to {end_date}\n"
            f"# Records: {len(df)}\n\n"
        )
        return header + csv_str

    except Exception as e:
        return f"Error fetching FRED macro data for '{series_id}': {e}"


def get_macro_snapshot(
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    lookback_days: Annotated[int, "Days to look back for latest available values"] = 90,
) -> str:
    """
    获取关键宏观指标快照（最新可用值）。
    一次性返回 Fed Funds Rate、CPI、失业率、VIX、10Y收益率等核心指标，
    供 Agent 快速了解宏观背景，无需逐个查询。
    """
    ref_date = datetime.strptime(date, "%Y-%m-%d")
    start = (ref_date - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    key_series = ["DFF", "CPIAUCSL", "UNRATE", "VIXCLS", "GS10", "GS2", "T10Y2Y"]
    results = []

    try:
        fred = _get_fred_client()
    except Exception as e:
        return f"FRED client initialization failed: {e}"

    for sid in key_series:
        try:
            series = fred.get_series(
                sid,
                observation_start=start,
                observation_end=date,
                realtime_start=date,
                realtime_end=date,
            )
            if series.empty:
                results.append(f"  {sid:<12} {MACRO_SERIES.get(sid, sid):<45} N/A")
                continue
            latest_val = series.dropna().iloc[-1]
            latest_date = series.dropna().index[-1].strftime("%Y-%m-%d")
            results.append(
                f"  {sid:<12} {MACRO_SERIES.get(sid, sid):<45} {latest_val:>8.2f}  (as of {latest_date})"
            )
        except Exception:
            results.append(f"  {sid:<12} {MACRO_SERIES.get(sid, sid):<45} ERROR")

    header = (
        f"# Macro Economic Snapshot\n"
        f"# Reference date: {date}\n"
        f"# Source: FRED (Federal Reserve Economic Data)\n\n"
        f"  {'Series ID':<12} {'Description':<45} {'Value':>8}  Last Updated\n"
        + "-" * 85 + "\n"
    )
    return header + "\n".join(results)


def list_available_macro_series() -> str:
    """列出所有可用的 FRED 宏观指标代码，供 Agent 参考查询。"""
    lines = ["# Available FRED Macro Indicators\n"]
    lines.append(f"  {'Series ID':<15} Description")
    lines.append("-" * 60)
    for sid, desc in MACRO_SERIES.items():
        lines.append(f"  {sid:<15} {desc}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 内部工具：本地缓存（供 #3 RAP 向量库读取）
# ─────────────────────────────────────────────────────────────────────────────

def _save_to_cache(df: pd.DataFrame, symbol: str, category: str, start: str, end: str):
    """写入 parquet 缓存，#3 直接读取，无需重复采集。"""
    try:
        from .local_cache import save_dataframe
        save_dataframe(df, symbol, category, start, end)
    except Exception:
        pass
