from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openrouter"
config["backend_url"] = "https://openrouter.ai/api/v1"
config["deep_think_llm"] = "deepseek/deepseek-v3.2"  # Use a different model
config["quick_think_llm"] = "qwen/qwen3.5-flash-02-23"  # Use a different model
config["max_debate_rounds"] = 2

# Configure data vendors
# 注意：直接赋值会替换整个 dict，务必保留全部 7 个 key
# 若只需修改个别 vendor，请用 config["data_vendors"]["key"] = "value"
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",    # Options: alpha_vantage, yfinance
    "technical_indicators": "alpha_vantage",  # Options: alpha_vantage, yfinance
    "fundamental_data": "alpha_vantage",  # Only: alpha_vantage (需要 ALPHA_VANTAGE_API_KEY)
    "news_data": "alpha_vantage",        # Only: alpha_vantage (需要 ALPHA_VANTAGE_API_KEY)
}

# ── 默认运行：NVDA 2024-05-10，标准四分析师组合 ──────────────────────────────
# 数据采集策略：批量预拉取（Bulk Prefetch）
# 首次调用自动拉取 5 年数据缓存到 ./data_cache/bulk/{TICKER}/
# 后续运行从本地切片返回，零 API 调用（离线可用）
# 新闻数据不缓存，每次实时拉取以保证相关性排序准确
ta = TradingAgentsGraph(
    selected_analysts=["market", "sentiment", "news", "fundamentals", "macro"],
    debug=True,
    config=config,
)
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns


# ─────────────────────────────────────────────────────────────────────────────
# 其他使用示例（取消注释以切换分析模式）
# ─────────────────────────────────────────────────────────────────────────────

# 标准股票分析——同上方默认运行，取消注释可独立使用
# ta2 = TradingAgentsGraph(selected_analysts=["market", "sentiment", "news", "fundamentals"], config=config)
# _, decision = ta2.propagate("NVDA", "2024-05-10")

