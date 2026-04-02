"""
轻量级本地数据缓存模块
策略：Parquet 文件存储（零依赖数据库，pandas 原生支持，压缩比高）
目录结构：
  data_cache/
    crypto/BTC/2024-01-01_2024-12-31.parquet
    macro/FEDFUNDS/2020-01-01_2024-12-31.parquet
    sentiment/NVDA/2024-05-10_2024-05-10.parquet
    stocks/NVDA/2024-01-01_2024-12-31.parquet

职责说明（#2 与 #3 的分工边界）：
  - #2（本模块）：负责写入缓存（save_dataframe）
  - #3（RAP 向量库）：负责读取缓存（load_dataframe）并向量化，不重复实现采集逻辑

历史数据是否必要？
  - 回测需要：必须。Agent 需要历史数据才能在过去日期做决策模拟。
  - 缓存价值：避免每次回测重复调用 API（CoinGecko 有 rate limit，FRED 有配额）。
  - 缓存机制：首次调用自动写入，后续命中缓存直接返回，显著提速。
"""

import os
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime

# 缓存根目录，默认放在项目根下的 data_cache/ 文件夹
_CACHE_ROOT = Path(os.getenv("TRADEHIVE_CACHE_DIR", "data_cache"))


def _cache_path(symbol: str, category: str, start: str, end: str) -> Path:
    """生成缓存文件路径：data_cache/{category}/{symbol}/{start}_{end}.parquet"""
    safe_symbol = symbol.upper().replace("/", "-").replace(":", "-")
    cache_dir = _CACHE_ROOT / category / safe_symbol
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{start}_{end}.parquet"
    return cache_dir / filename


def save_dataframe(
    df: pd.DataFrame,
    symbol: str,
    category: str,
    start: str,
    end: str,
) -> Path:
    """
    将 DataFrame 存储为 parquet 格式。
    - 自动创建目录，不存在时创建
    - 同名文件直接覆盖（最新数据优先）
    - 返回实际写入路径
    """
    path = _cache_path(symbol, category, start, end)
    df.to_parquet(path, index=False, compression="snappy")
    return path


def load_dataframe(
    symbol: str,
    category: str,
    start: str,
    end: str,
) -> pd.DataFrame | None:
    """
    从 parquet 缓存加载 DataFrame。
    - 命中缓存返回 DataFrame
    - 未命中返回 None（调用方决定是否回落到 API 采集）
    #3 RAP 向量库直接调用此函数读取历史数据，无需重复实现采集逻辑。
    """
    path = _cache_path(symbol, category, start, end)
    if path.exists():
        return pd.read_parquet(path)
    return None


def list_cache(category: str = None) -> list[dict]:
    """
    列出缓存中的所有文件，便于调试和管理。
    返回: [{"category": str, "symbol": str, "start": str, "end": str, "size_kb": float}]
    """
    root = _CACHE_ROOT if not category else _CACHE_ROOT / category
    if not root.exists():
        return []

    entries = []
    for f in root.rglob("*.parquet"):
        parts = f.relative_to(_CACHE_ROOT).parts
        if len(parts) >= 3:
            cat = parts[0]
            sym = parts[1]
            stem = f.stem  # "2024-01-01_2024-12-31"
            dates = stem.split("_", 1)
            entries.append({
                "category": cat,
                "symbol": sym,
                "start": dates[0] if len(dates) > 0 else "",
                "end": dates[1] if len(dates) > 1 else "",
                "size_kb": round(f.stat().st_size / 1024, 1),
                "path": str(f),
            })
    return entries


def clear_cache(category: str = None, symbol: str = None):
    """
    清理缓存。可选指定 category 和/或 symbol 范围清理，
    不传参数则清理全部缓存（谨慎使用）。
    """
    import shutil
    if symbol and category:
        target = _CACHE_ROOT / category / symbol.upper().replace("/", "-")
    elif category:
        target = _CACHE_ROOT / category
    else:
        target = _CACHE_ROOT

    if target.exists():
        shutil.rmtree(target)


def get_cache_summary() -> str:
    """返回缓存状态摘要，供调试使用。"""
    entries = list_cache()
    if not entries:
        return f"Cache is empty. Root: {_CACHE_ROOT.resolve()}"

    total_size = sum(e["size_kb"] for e in entries)
    cats = {}
    for e in entries:
        cats.setdefault(e["category"], []).append(e["symbol"])

    lines = [
        f"# Data Cache Summary",
        f"# Root: {_CACHE_ROOT.resolve()}",
        f"# Total files: {len(entries)} | Total size: {total_size:.1f} KB\n",
    ]
    for cat, symbols in cats.items():
        unique_syms = sorted(set(symbols))
        lines.append(f"  [{cat}] {len(unique_syms)} symbols: {', '.join(unique_syms)}")
    return "\n".join(lines)
