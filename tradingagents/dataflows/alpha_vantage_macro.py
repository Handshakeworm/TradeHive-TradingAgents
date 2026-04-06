"""
Alpha Vantage 宏观经济指标数据模块

覆盖端点：
- FEDERAL_FUNDS_RATE：联邦基金利率
- CPI：消费者价格指数
- REAL_GDP：实际 GDP
- UNEMPLOYMENT：失业率
- TREASURY_YIELD：国债收益率

所有函数均接受 curr_date 参数，过滤未来数据防止回测泄漏。
"""

import json
import pandas as pd
from .alpha_vantage_common import _make_api_request


def _filter_macro_by_date(raw_json: str, curr_date: str = None, limit: int = 24) -> str:
    """
    从 AV 宏观端点返回的 JSON 中过滤数据，防止回测数据泄漏。

    AV 宏观数据格式：
    {
        "name": "...",
        "interval": "monthly",
        "unit": "percent",
        "data": [{"date": "2024-01-01", "value": "5.33"}, ...]
    }
    data 列表已按日期降序排列。

    Args:
        raw_json: AV API 返回的原始 JSON 字符串
        curr_date: 回测截止日期（只保留 date <= curr_date 的数据），None 表示不过滤
        limit: 最多返回的数据点数量

    Returns:
        格式化为 Markdown 表格的字符串
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return f"Error: Invalid JSON response from Alpha Vantage."

    if "Information" in data or "Error Message" in data:
        msg = data.get("Information") or data.get("Error Message", "Unknown error")
        return f"Alpha Vantage API error: {msg}"

    name = data.get("name", "Unknown Indicator")
    interval = data.get("interval", "")
    unit = data.get("unit", "")
    rows = data.get("data", [])

    if not rows:
        return f"No data available for {name}."

    # 过滤：移除缺失值（AV 用 "." 表示缺失）并按 curr_date 截止
    if curr_date:
        cutoff = pd.to_datetime(curr_date)
        filtered = [
            r for r in rows
            if r.get("value", ".") != "."
            and pd.to_datetime(r["date"]) <= cutoff
        ]
    else:
        filtered = [r for r in rows if r.get("value", ".") != "."]

    if not filtered:
        return f"No data available for {name} on or before {curr_date}."

    # 取最近 limit 条（AV 已按降序排列，取前 limit 条即最新数据）
    recent = filtered[:limit]

    # 构建 Markdown 表格
    lines = [
        f"# {name}",
        f"- Interval: {interval} | Unit: {unit}",
        f"- Showing {len(recent)} most recent data points (up to {curr_date or 'latest'})",
        "",
        "| Date | Value |",
        "|------|-------|",
    ]
    for row in recent:
        lines.append(f"| {row['date']} | {row['value']} |")

    return "\n".join(lines)


def get_federal_funds_rate(interval: str = "monthly", curr_date: str = None) -> str:
    """
    获取美联储联邦基金利率历史数据。

    Args:
        interval: 数据频率，daily / weekly / monthly（默认 monthly）
        curr_date: 回测截止日期 yyyy-mm-dd

    Returns:
        Markdown 格式的利率时间序列
    """
    params = {"interval": interval}
    raw = _make_api_request("FEDERAL_FUNDS_RATE", params)
    return _filter_macro_by_date(raw, curr_date)


def get_cpi(interval: str = "monthly", curr_date: str = None) -> str:
    """
    获取美国消费者价格指数（CPI）历史数据。

    Args:
        interval: 数据频率，monthly / semiannual（默认 monthly）
        curr_date: 回测截止日期 yyyy-mm-dd

    Returns:
        Markdown 格式的 CPI 时间序列
    """
    params = {"interval": interval}
    raw = _make_api_request("CPI", params)
    return _filter_macro_by_date(raw, curr_date)


def get_real_gdp(interval: str = "quarterly", curr_date: str = None) -> str:
    """
    获取美国实际 GDP 历史数据。

    Args:
        interval: 数据频率，annual / quarterly（默认 quarterly）
        curr_date: 回测截止日期 yyyy-mm-dd

    Returns:
        Markdown 格式的 GDP 时间序列
    """
    params = {"interval": interval}
    raw = _make_api_request("REAL_GDP", params)
    return _filter_macro_by_date(raw, curr_date)


def get_unemployment(curr_date: str = None) -> str:
    """
    获取美国失业率历史数据（月度）。

    Args:
        curr_date: 回测截止日期 yyyy-mm-dd

    Returns:
        Markdown 格式的失业率时间序列
    """
    raw = _make_api_request("UNEMPLOYMENT", {})
    return _filter_macro_by_date(raw, curr_date)


def get_treasury_yield(interval: str = "monthly", maturity: str = "10year", curr_date: str = None) -> str:
    """
    获取美国国债收益率历史数据。

    Args:
        interval: 数据频率，daily / weekly / monthly（默认 monthly）
        maturity: 债券期限，3month / 2year / 5year / 7year / 10year / 30year（默认 10year）
        curr_date: 回测截止日期 yyyy-mm-dd

    Returns:
        Markdown 格式的国债收益率时间序列
    """
    params = {"interval": interval, "maturity": maturity}
    raw = _make_api_request("TREASURY_YIELD", params)
    return _filter_macro_by_date(raw, curr_date)
