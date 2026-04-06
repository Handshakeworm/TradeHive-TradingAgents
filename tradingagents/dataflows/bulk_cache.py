"""
批量数据缓存模块
策略：每个 (ticker, data_type) 只存一份完整数据文件，查询时按需切片。

目录结构：
  data_cache/
    bulk/
      AAPL/
        stock_data.csv
        stock_data.meta.json
        indicator_rsi.csv
        balance_sheet_quarterly.csv
        insider_transactions.csv
      _global/
        ...

集成点：interface.py 的 _try_bulk_cache() 调用本模块。
"""

import json
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd

from .config import get_config


def _bulk_dir(ticker: str) -> Path:
    """获取 ticker 的批量缓存目录。"""
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    return cache_dir / "bulk" / ticker.upper()


def _data_path(ticker: str, data_type: str, ext: str = ".csv") -> Path:
    return _bulk_dir(ticker) / f"{data_type}{ext}"


def _meta_path(ticker: str, data_type: str) -> Path:
    return _bulk_dir(ticker) / f"{data_type}.meta.json"


def bulk_has(ticker: str, data_type: str, ext: str = ".csv") -> bool:
    """检查批量缓存是否存在。"""
    return _data_path(ticker, data_type, ext).exists()


def bulk_load(ticker: str, data_type: str, ext: str = ".csv") -> str:
    """读取完整缓存文件内容。"""
    return _data_path(ticker, data_type, ext).read_text(encoding="utf-8")


def bulk_save(ticker: str, data_type: str, raw_data: str, meta: dict = None, ext: str = ".csv"):
    """写入原始数据 + 元数据。"""
    path = _data_path(ticker, data_type, ext)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw_data, encoding="utf-8")

    if meta:
        meta_p = _meta_path(ticker, data_type)
        meta["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_comment_header(text: str) -> str:
    """去掉文本开头的 # 注释行和空行，返回纯数据部分。"""
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            start = i
            break
    return "\n".join(lines[start:])


def slice_csv_by_range(csv_text: str, start_date: str, end_date: str) -> str:
    """从 CSV 中按日期范围 [start, end] 切片。

    自动检测第一列为日期列。返回过滤后的 CSV 字符串（含列头）。
    """
    if not csv_text or not csv_text.strip():
        return csv_text

    try:
        df = pd.read_csv(StringIO(csv_text))
        if df.empty:
            return csv_text

        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        filtered = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)]

        return filtered.to_csv(index=False)
    except Exception:
        return csv_text


def slice_csv_before(csv_text: str, curr_date: str, date_col: str = None) -> str:
    """从 CSV 中取 date ≤ curr_date 的行。

    用于 balance_sheet、cashflow、income_statement、insider_transactions。
    自动检测日期列：优先使用 reportedDate，其次 Start Date，最后第一列。
    """
    if not csv_text or not csv_text.strip():
        return csv_text

    try:
        df = pd.read_csv(StringIO(csv_text))
        if df.empty:
            return csv_text

        # 确定日期列
        if date_col and date_col in df.columns:
            col = date_col
        elif "reportedDate" in df.columns:
            col = "reportedDate"
        elif "Start Date" in df.columns:
            col = "Start Date"
        else:
            col = df.columns[0]

        df[col] = pd.to_datetime(df[col], errors="coerce")
        cutoff = pd.to_datetime(curr_date)
        filtered = df[df[col] <= cutoff]

        return filtered.to_csv(index=False)
    except Exception:
        return csv_text


def slice_json_news(json_text: str, start_date: str, end_date: str, limit: int = None) -> str:
    """从 AV NEWS_SENTIMENT JSON 中按 time_published 切片。

    Args:
        json_text: Alpha Vantage NEWS_SENTIMENT 原始 JSON 字符串
        start_date: 开始日期 yyyy-mm-dd
        end_date: 结束日期 yyyy-mm-dd
        limit: 最多返回条数（None 表示不限）

    Returns:
        过滤后的 JSON 字符串
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        # 非 JSON 格式（可能是纯文本），原样返回
        return json_text

    feed = data.get("feed", [])
    if not feed:
        return json_text

    # time_published 格式: "YYYYMMDDTHHMMSS"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    filtered = []
    for item in feed:
        tp = item.get("time_published", "")
        if len(tp) < 8:
            continue
        try:
            item_dt = datetime.strptime(tp[:15], "%Y%m%dT%H%M%S")
        except ValueError:
            try:
                item_dt = datetime.strptime(tp[:8], "%Y%m%d")
            except ValueError:
                continue

        if start_dt <= item_dt <= end_dt:
            filtered.append(item)

    if limit is not None:
        filtered = filtered[:limit]

    data["feed"] = filtered
    data["items"] = str(len(filtered))
    return json.dumps(data, ensure_ascii=False)


def bulk_clear(ticker: str = None):
    """清理批���缓存。指定 ticker 清理该 ticker，不传清理全部。"""
    import shutil

    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    bulk_root = cache_dir / "bulk"

    if ticker:
        target = bulk_root / ticker.upper()
    else:
        target = bulk_root

    if target.exists():
        shutil.rmtree(target)
