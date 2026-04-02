from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openrouter"
config["backend_url"] = "https://openrouter.ai/api/v1"
config["deep_think_llm"] = "gpt-5-mini"  # Use a different model
config["quick_think_llm"] = "gpt-5-mini"  # Use a different model
config["max_debate_rounds"] = 1

# Configure data vendors
# 注意：直接赋值会替换整个 dict，务必保留全部 7 个 key
# 若只需修改个别 vendor，请用 config["data_vendors"]["key"] = "value"
config["data_vendors"] = {
    # ── 原有股票数据（按需拉取，首次调用后自动缓存到 data_cache/ Parquet） ──
    "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
    "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
    "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
    "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    # ── 新增数据类别（免费，见 .env.example for API keys） ──────────────────
    "crypto_data": "coingecko",          # CoinGecko 实时价格 + yfinance 历史；无需 Key
    "macro_data": "fred",                # FRED 宏观指标；需 FRED_API_KEY（.env）
    "sentiment_data": "vader",           # VADER 离线情绪评分；无需 Key
}

# ── 默认运行：NVDA 2024-05-10，标准四分析师组合 ──────────────────────────────
# 数据采集策略：按需实时拉取（On-demand Fetch）
# 首次调用自动缓存到 ./data_cache/{category}/{symbol}/*.parquet
# 后续运行命中缓存则跳过 API 调用（离线可用）
ta = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
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
# ta2 = TradingAgentsGraph(selected_analysts=["market", "social", "news", "fundamentals"], config=config)
# _, decision = ta2.propagate("NVDA", "2024-05-10")

# 加密货币分析（crypto + sentiment，不需要 FRED API Key）
# crypto_config = DEFAULT_CONFIG.copy()
# crypto_config["llm_provider"] = "openrouter"
# crypto_config["backend_url"] = "https://openrouter.ai/api/v1"
# crypto_config["quick_think_llm"] = "gpt-5-mini"
# crypto_config["deep_think_llm"] = "gpt-5-mini"
# ta_crypto = TradingAgentsGraph(selected_analysts=["crypto", "sentiment", "fundamentals"], config=crypto_config)
# _, decision = ta_crypto.propagate("BTC", "2024-05-10")

# 全量分析（含宏观加分项，需要 FRED_API_KEY 配置在 .env）
# ta_full = TradingAgentsGraph(
#     selected_analysts=["market", "social", "news", "fundamentals", "sentiment", "crypto", "macro"],
#     config=crypto_config,
# )
# _, decision = ta_full.propagate("BTC", "2024-05-10")
