"""Pull full AAPL cache — same as NVDA."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from tradingagents.dataflows.interface import route_to_vendor

TICKER = "GOOGL"
CURR_DATE = "2026-04-05"

# ── 1. Stock data ──
print("=" * 60)
print("[1/8] Stock data")
r = route_to_vendor("get_stock_data", TICKER, CURR_DATE, 30)
print(f"  → {len(r)} chars")

# ── 2. Indicators (7 groups, 11 indicators) ──
indicators = [
    "close_50_sma", "close_200_sma", "close_10_ema",
    "macd", "rsi", "boll", "atr",
]
print("=" * 60)
print("[2/8] Indicators (7 groups)")
for ind in indicators:
    r = route_to_vendor("get_indicators", TICKER, ind, CURR_DATE, 30)
    print(f"  {ind}: {len(r) if r else 0} chars")
    time.sleep(1.5)

# ── 3. Financial statements (3 types) ──
print("=" * 60)
print("[3/8] Financial statements")
for method in ["get_balance_sheet", "get_cashflow", "get_income_statement"]:
    r = route_to_vendor(method, TICKER, "quarterly", CURR_DATE)
    print(f"  {method}: {len(r)} chars")
    time.sleep(1.5)

# ── 4. Fundamentals (FMP, self-managed cache) ──
print("=" * 60)
print("[4/8] Fundamentals")
r = route_to_vendor("get_fundamentals", TICKER, CURR_DATE)
print(f"  → {len(r)} chars")

# ── 5. Insider transactions ──
print("=" * 60)
print("[5/8] Insider transactions")
r = route_to_vendor("get_insider_transactions", TICKER, CURR_DATE)
print(f"  → {len(r)} chars")

# ── 6. News (segmented, ~6 min) ──
print("=" * 60)
print("[6/8] News (segmented fetch, may take several minutes...)")
r = route_to_vendor("get_news", TICKER, "2023-06-01", "2023-06-15")
print(f"  → {len(r)} chars")

# ── 7. Global news (already cached in _GLOBAL/) ──
print("=" * 60)
print("[7/8] Global news (shared cache)")
r = route_to_vendor("get_global_news", CURR_DATE, 7, 5)
print(f"  → {len(r)} chars")

print("=" * 60)
print("AAPL cache pull complete!")
