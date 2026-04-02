from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.macro_tools import (
    get_macro_indicator,
    get_macro_snapshot,
    list_available_macro_series,
)


def create_macro_analyst(llm):
    """
    Macro Event Analyst Agent (bonus / extra-credit agent per DEV_SPEC).

    Analyzes macroeconomic conditions from FRED data:
    - Interest rate environment (FEDFUNDS, GS10, GS2, T10Y2Y)
    - Inflation (CPIAUCSL, CPILFESL, PCEPI)
    - Employment (UNRATE, PAYEMS, ICSA)
    - Market stress (VIXCLS, M2SL)

    Writes to state["news_report"] — can be selected as a replacement for
    "news" analyst when macro context is more relevant than company news,
    or used alongside news analyst for richer context.
    """

    def macro_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_macro_snapshot,
            get_macro_indicator,
            list_available_macro_series,
        ]

        system_message = (
            "You are a macroeconomic research analyst specializing in understanding "
            "how macro conditions affect equity and crypto asset prices. "
            "Your job is to assess the current macroeconomic environment and its "
            "implications for the target instrument.\n\n"
            "Workflow:\n"
            "1. Start with get_macro_snapshot(date) for a quick overview of current conditions\n"
            "2. Use get_macro_indicator() to pull detailed history on the most relevant series:\n"
            "   - Rate environment: FEDFUNDS, GS10, GS2, T10Y2Y (yield curve inversion?)\n"
            "   - Inflation: CPIAUCSL or CPILFESL (trending up or cooling?)\n"
            "   - Labor market: UNRATE, PAYEMS (employment strength)\n"
            "   - Market stress: VIXCLS (fear gauge), M2SL (liquidity)\n"
            "3. Use list_available_macro_series() if you need to discover other series IDs\n\n"
            "Structure your macro report:\n"
            "1. **Rate & Monetary Policy Outlook**: Fed trajectory, rate level, yield curve shape\n"
            "2. **Inflation Regime**: CPI/PCE trend — above/below target, direction of change\n"
            "3. **Employment & Growth**: Labor market strength, GDP trajectory\n"
            "4. **Market Stress Indicators**: VIX level and trend, credit spreads if available\n"
            "5. **Macro Impact on Target Asset**: Tailwinds vs. headwinds for the instrument\n"
            "6. **Overall Macro Signal**: BULLISH / NEUTRAL / BEARISH macro backdrop\n"
            "7. **Markdown Table**: Key macro indicators with latest values and trend direction\n\n"
            "Be quantitative — always cite specific values and dates from tool outputs."
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
            "news_report": report,
        }

    return macro_analyst_node
