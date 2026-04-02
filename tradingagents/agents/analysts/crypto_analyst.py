from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.crypto_tools import (
    get_crypto_price,
    get_crypto_historical,
    get_crypto_market_overview,
)
from tradingagents.agents.utils.macro_tools import get_macro_snapshot


def create_crypto_analyst(llm):
    """
    Crypto Market Analyst Agent.

    Focused on cryptocurrency market analysis:
    - Real-time price snapshot (CoinGecko, no API key)
    - Historical OHLCV for trend analysis
    - Crypto market overview (top 10 by market cap)
    - Macro snapshot for rate/VIX context alongside crypto

    Writes to state["market_report"] — use as a drop-in replacement for
    "market" analyst when the instrument is a crypto asset, or select both
    to get parallel stock + crypto analysis.
    """

    def crypto_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_crypto_price,
            get_crypto_historical,
            get_crypto_market_overview,
            get_macro_snapshot,
        ]

        system_message = (
            "You are a cryptocurrency market analyst with deep expertise in on-chain "
            "metrics, crypto market structure, and macro-crypto correlations. "
            "Your objective is to produce a comprehensive crypto market analysis report.\n\n"
            "Use the following tools:\n"
            "- get_crypto_price(): Real-time price snapshot with market cap, volume, "
            "and short-term price change percentages\n"
            "- get_crypto_historical(): Historical daily OHLCV data for trend and "
            "momentum analysis (suggest at least 90 days lookback)\n"
            "- get_crypto_market_overview(): Top 10 coins by market cap; assess overall "
            "crypto market risk-on/risk-off sentiment\n"
            "- get_macro_snapshot(): Current Fed Funds Rate, CPI, VIX, and yield curve; "
            "assess macro tailwinds/headwinds for crypto\n\n"
            "Structure your report:\n"
            "1. **Price Action**: Current price, key support/resistance, recent volatility\n"
            "2. **Trend Analysis**: 7d / 30d / 90d momentum, moving averages if derivable\n"
            "3. **Market Context**: Where does this coin stand vs. the broader crypto market?\n"
            "4. **Macro Overlay**: Rate environment is risk-on or risk-off for crypto?\n"
            "5. **Risk Assessment**: Key downside risks (regulatory, liquidity, correlation)\n"
            "6. **Trading Signal**: BUY / HOLD / SELL with concise rationale\n"
            "7. **Markdown Table**: Key metrics summary\n\n"
            "Be specific and quantitative. Cite actual numbers from the tool outputs."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([t.name for t in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "crypto_report": report,
        }

    return crypto_analyst_node
