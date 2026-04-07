import logging

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.backtesting import BacktestEngine
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openrouter"
config["backend_url"] = "https://openrouter.ai/api/v1"
config["deep_think_llm"] = "deepseek/deepseek-v3.2"
config["quick_think_llm"] = "xiaomi/mimo-v2-flash"
config["max_debate_rounds"] = 2
config["max_risk_discuss_rounds"] = 2

# Configure data vendors
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",
    "technical_indicators": "alpha_vantage",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

# ── 初始化 Agent 图 ──────────────────────────────────────────────────────────
ta = TradingAgentsGraph(
    selected_analysts=["market", "sentiment", "news", "fundamentals", "macro"],
    debug=True,
    config=config,
)

# ── 回测模式 ─────────────────────────────────────────────────────────────────
engine = BacktestEngine(ta, initial_capital=100_000)
results = engine.run("NVDA", "2025-02-14", "2025-08-14")

print(f"\nBacktest complete: {results['ticker']}")
print(f"  Period: {results['start_date']} ~ {results['end_date']}")
print(f"  Trading days: {results['trading_days']}")
print(f"  Initial capital: ${results['initial_capital']:,.0f}")
print(f"  Final value: ${results['final_value']:,.2f}")
print(f"  Total return: {results['total_return_pct']:.2f}%")

# ── 单次分析模式（取消注释使用）──────────────────────────────────────────────
# _, decision = ta.propagate("NVDA", "2024-05-10")
# print(decision)
