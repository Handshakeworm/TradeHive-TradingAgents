import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
        # ── 新增数据类别（均为免费，见下方说明） ──────────────────────────────
        "crypto_data": "coingecko",          # CoinGecko 免费无需 API Key
        "macro_data": "fred",                # FRED 免费，需在 .env 中配置 FRED_API_KEY
        "sentiment_data": "vader",           # VADER 纯离线，无需 API Key
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # ── 数据缓存配置 ─────────────────────────────────────────────────────────
    # 历史数据缓存目录（parquet 格式，#3 RAP 向量库直接读取）
    # 设为 None 可禁用缓存（不推荐，会导致每次回测重复调用 API）
    "data_cache_enabled": True,
    "data_cache_dir": os.getenv("TRADEHIVE_CACHE_DIR", "./data_cache"),
}
