"""验证 data_cache/bulk/ 下所有缓存文件的完整性。"""
import json
import os
from io import StringIO
from pathlib import Path

import pandas as pd

BULK_DIR = Path(__file__).parent / "data_cache" / "bulk"

# 每个 ticker 应有的完整文件集（不含 meta）
EXPECTED_FILES = {
    "stock_data.csv",
    "indicator_raw_sma_50.csv",
    "indicator_raw_sma_200.csv",
    "indicator_raw_ema_10.csv",
    "indicator_raw_macd.csv",
    "indicator_raw_rsi.csv",
    "indicator_raw_bbands.csv",
    "indicator_raw_atr.csv",
    "balance_sheet_quarterly.csv",
    "cashflow_quarterly.csv",
    "income_statement_quarterly.csv",
    "balance_sheet.json",
    "income_statement.json",
    "cash_flow.json",
    "earnings.json",
    "insider_transactions.csv",
    "news.txt",
}

pass_count = 0
fail_count = 0
warn_count = 0


def result(status, path, msg):
    global pass_count, fail_count, warn_count
    tag = {"PASS": "\033[32m[PASS]\033[0m", "FAIL": "\033[31m[FAIL]\033[0m",
           "WARN": "\033[33m[WARN]\033[0m", "ORPHAN": "\033[35m[ORPHAN]\033[0m"}
    print(f"{tag.get(status, status)} {path} — {msg}")
    if status == "PASS":
        pass_count += 1
    elif status == "FAIL":
        fail_count += 1
    else:
        warn_count += 1


def check_csv(filepath, required_cols, min_rows=5, label=None):
    """检查 CSV 文件：可解析、含必要列、行数足够。"""
    rel = filepath.relative_to(BULK_DIR)
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        result("FAIL", rel, f"无法解析为 CSV: {e}")
        return False

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        result("FAIL", rel, f"缺少列 {missing}，实际列: {list(df.columns[:8])}")
        return False

    if len(df) < min_rows:
        result("FAIL", rel, f"行数过少: {len(df)} (期望 >= {min_rows})")
        return False

    # 日期范围
    date_col = required_cols[0]
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if not dates.empty:
        result("PASS", rel, f"{len(df)} rows, {dates.min().date()} ~ {dates.max().date()}")
    else:
        result("PASS", rel, f"{len(df)} rows")
    return True


def check_json_fundamentals(filepath):
    """检查财报 JSON 文件。"""
    rel = filepath.relative_to(BULK_DIR)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        result("FAIL", rel, f"无法解析为 JSON: {e}")
        return False

    if not isinstance(data, dict):
        result("FAIL", rel, f"JSON 顶层不是 dict")
        return False

    for err_key in ("Error Message", "Information"):
        if err_key in data:
            result("FAIL", rel, f"含错误键 '{err_key}': {str(data[err_key])[:80]}")
            return False

    # 检查数据数组
    for key in ("quarterlyReports", "annualReports", "quarterlyEarnings", "annualEarnings"):
        arr = data.get(key)
        if arr and isinstance(arr, list) and len(arr) > 0:
            result("PASS", rel, f"{key}: {len(arr)} records")
            return True

    result("FAIL", rel, f"无有效数据数组，键: {list(data.keys())[:6]}")
    return False


def check_news(filepath, min_articles=1000):
    """检查新闻 JSON 文件。"""
    rel = filepath.relative_to(BULK_DIR)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        result("FAIL", rel, f"无法解析为 JSON: {e}")
        return False

    if not isinstance(data, dict):
        result("FAIL", rel, f"JSON 顶层不是 dict")
        return False

    for err_key in ("Error Message", "Information"):
        if err_key in data:
            result("FAIL", rel, f"含错误键 '{err_key}'")
            return False

    feed = data.get("feed", [])
    if not feed:
        result("FAIL", rel, f"feed 数组为空或不存在")
        return False

    count = len(feed)
    # 检查日期范围
    times = []
    for item in (feed[0], feed[-1]):
        tp = item.get("time_published", "")[:8]
        if tp:
            times.append(tp)
    date_info = f", dates: {' ~ '.join(times)}" if times else ""

    if count < min_articles:
        result("WARN", rel, f"{count} articles (期望 >= {min_articles}){date_info}")
    else:
        result("PASS", rel, f"{count} articles{date_info}")
    return True


def check_ticker(ticker_dir):
    """检查一个 ticker 目录的所有文件。"""
    ticker = ticker_dir.name
    files = {f.name for f in ticker_dir.iterdir() if f.is_file()}
    data_files = {f for f in files if not f.endswith(".meta.json")}

    # 检查各类文件
    for fname in sorted(data_files):
        fpath = ticker_dir / fname

        if fname == "stock_data.csv":
            check_csv(fpath, ["timestamp", "open", "high", "low", "close", "volume"], min_rows=100)

        elif fname.startswith("indicator_raw_") and fname.endswith(".csv"):
            check_csv(fpath, ["time"], min_rows=100)

        elif fname in ("balance_sheet_quarterly.csv", "cashflow_quarterly.csv", "income_statement_quarterly.csv"):
            check_csv(fpath, ["fiscalDateEnding"], min_rows=5)

        elif fname in ("balance_sheet.json", "income_statement.json", "cash_flow.json", "earnings.json"):
            check_json_fundamentals(fpath)

        elif fname == "insider_transactions.csv":
            check_csv(fpath, ["transaction_date"], min_rows=20)

        elif fname in ("news.txt",):
            check_news(fpath, min_articles=1000)

        elif fname in ("global_news.txt",):
            check_news(fpath, min_articles=1000)

        else:
            result("WARN", fpath.relative_to(BULK_DIR), f"未知文件类型")

    # 检查缺失的核心文件（仅对非特殊目录）
    if ticker not in ("_GLOBAL",):
        missing = EXPECTED_FILES - data_files
        if missing:
            result("WARN", f"{ticker}/", f"缺少 {len(missing)} 个文件: {sorted(missing)[:5]}")


def main():
    if not BULK_DIR.exists():
        print(f"缓存目录不存在: {BULK_DIR}")
        return

    print(f"扫描缓存目录: {BULK_DIR}\n")

    # 检查根目录孤儿文件
    for item in sorted(BULK_DIR.iterdir()):
        if item.is_file():
            result("ORPHAN", item.relative_to(BULK_DIR), "不属于任何 ticker 目录")

    # 遍历 ticker 目录
    for item in sorted(BULK_DIR.iterdir()):
        if item.is_dir():
            print(f"\n{'─' * 50}")
            print(f"  {item.name}")
            print(f"{'─' * 50}")
            check_ticker(item)

    # 汇总
    print(f"\n{'=' * 50}")
    print(f"  汇总: {pass_count} PASS, {fail_count} FAIL, {warn_count} WARN")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
