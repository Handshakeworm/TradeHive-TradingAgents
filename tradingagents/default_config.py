import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
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
        "core_stock_apis": "alpha_vantage",      # Options: alpha_vantage, yfinance
        "technical_indicators": "alpha_vantage",  # Options: alpha_vantage, yfinance
        "fundamental_data": "alpha_vantage",      # Only: alpha_vantage
        "news_data": "alpha_vantage",             # Only: alpha_vantage
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # ── 数据缓存配置 ─────────────────────────────────────────────────────────
    "data_cache_dir": os.getenv("TRADEHIVE_CACHE_DIR", "./data_cache"),
    # 按请求缓存（仅用于非 bulk 方法）
    "data_cache_enabled": True,
    # ── 批量缓存配置 ─────────────────────────────────────────────────────────
    # 首次请求时一次性拉取大范围数据存到本地，后续查询从本地切片
    "bulk_cache_enabled": True,
    "bulk_cache_prefetch_years": 5,       # 统一预拉取年数
}
