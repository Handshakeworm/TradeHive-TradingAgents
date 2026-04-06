"""
轻量级本地数据缓存模块
策略：纯文本文件存储（所有 tool 返回值均为 str）
目录结构：
  data_cache/
    get_stock_data/NVDA__2024-01-01__2024-05-10.txt
    get_indicators/NVDA__rsi__2024-05-10__30.txt
    get_fundamentals/NVDA__2024-05-10.txt

集成点：route_to_vendor() 调用前查缓存，未命中则调 API 后写入。
回测场景下同参数结果不变，缓存命中后零 API 调用。
"""

import hashlib
import re
from pathlib import Path

from .config import get_config

_MAX_FILENAME_LEN = 200


def _sanitize(value: str) -> str:
    """将参数值转为安全的文件名片段：大写、替换特殊字符。"""
    s = str(value).upper().strip()
    s = re.sub(r'[\\/:*?"<>|\s]+', "-", s)  # 替换文件系统不安全字符
    s = s.strip("-")
    return s or "_EMPTY_"


def _cache_path(method: str, args: tuple, kwargs: dict) -> Path | None:
    """
    生成缓存文件路径。
    返回 None 表示缓存被禁用。
    路径格式：{cache_dir}/{method}/{arg1}__{arg2}__{...}.txt
    文件名过长时回退到 hash。
    """
    config = get_config()
    if not config.get("data_cache_enabled", True):
        return None

    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))

    # 拼接所有参数作为文件名
    parts = [_sanitize(a) for a in args]
    for k in sorted(kwargs.keys()):
        parts.append(_sanitize(kwargs[k]))

    filename = "__".join(parts) if parts else "_NO_ARGS_"

    if len(filename) > _MAX_FILENAME_LEN:
        # 回退到 hash，但保留前 40 字符供人类识别
        h = hashlib.sha256(filename.encode()).hexdigest()[:16]
        filename = f"{filename[:40]}__{h}"

    method_dir = cache_dir / method
    method_dir.mkdir(parents=True, exist_ok=True)
    return method_dir / f"{filename}.txt"


def load_cache(method: str, args: tuple, kwargs: dict) -> str | None:
    """
    从缓存加载结果。
    命中返回 str，未命中返回 None。
    """
    path = _cache_path(method, args, kwargs)
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return None


def save_cache(method: str, args: tuple, kwargs: dict, result: str) -> Path | None:
    """
    将 API 返回的 str 结果写入缓存。
    返回写入路径，缓存禁用时返回 None。
    """
    path = _cache_path(method, args, kwargs)
    if path:
        path.write_text(result, encoding="utf-8")
        return path
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 管理工具
# ─────────────────────────────────────────────────────────────────────────────

def list_cache(method: str = None) -> list[dict]:
    """
    列出缓存中的所有文件（含按���求缓存和批量缓存），便于调试和管理。
    返回: [{"method": str, "filename": str, "size_kb": float, "path": str}]
    """
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    root = cache_dir / method if method else cache_dir
    if not root.exists():
        return []

    entries = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        # 跳过 meta.json 文件，只列数据文件
        if f.suffix == ".json" and f.stem.endswith(".meta"):
            continue
        rel = f.relative_to(cache_dir)
        entries.append({
            "method": rel.parts[0] if len(rel.parts) >= 2 else "",
            "filename": f.stem,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "path": str(f),
        })
    return entries


def clear_cache(method: str = None):
    """
    清理缓存（含按请求缓存和批量缓存）。
    可选指定 method 范围清理，不传参数则清理全部缓存。
    """
    import shutil
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    target = cache_dir / method if method else cache_dir
    if target.exists():
        shutil.rmtree(target)


def get_cache_summary() -> str:
    """返回缓存状态摘要（含按请求缓存和批量缓存），供调试使用。"""
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "./data_cache"))
    entries = list_cache()
    if not entries:
        return f"Cache is empty. Root: {cache_dir.resolve()}"

    # 分类统计：bulk vs per-request
    bulk_entries = [e for e in entries if e["method"] == "bulk"]
    request_entries = [e for e in entries if e["method"] != "bulk"]

    total_size = sum(e["size_kb"] for e in entries)
    methods = {}
    for e in entries:
        methods.setdefault(e["method"], 0)
        methods[e["method"]] += 1

    lines = [
        f"# Data Cache Summary",
        f"# Root: {cache_dir.resolve()}",
        f"# Total files: {len(entries)} | Total size: {total_size:.1f} KB",
        f"# Bulk cache: {len(bulk_entries)} files | Per-request cache: {len(request_entries)} files\n",
    ]
    for m, count in sorted(methods.items()):
        lines.append(f"  [{m}] {count} files")
    return "\n".join(lines)
