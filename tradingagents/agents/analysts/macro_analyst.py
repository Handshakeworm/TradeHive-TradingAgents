from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.macro_tools import (
    get_federal_funds_rate,
    get_cpi,
    get_real_gdp,
    get_unemployment,
    get_treasury_yield,
    get_dxy,
)
from tradingagents.agents.utils.sentiment_tools import get_vix


def create_macro_analyst(llm):
    def macro_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        instrument_context = build_instrument_context(ticker)

        tools = [
            get_federal_funds_rate,
            get_cpi,
            get_real_gdp,
            get_unemployment,
            get_treasury_yield,
            get_dxy,
            get_vix,
        ]

        system_message = (
            f"You are a macroeconomic analyst tasked with assessing how the current macro environment "
            f"affects {ticker} specifically — not the economy in general. "
            "Your workflow: "
            f"1) Call get_federal_funds_rate(curr_date) and get_treasury_yield(curr_date, maturity='10year') "
            f"to understand monetary policy stance and yield curve shape, then analyze how current rate levels "
            f"affect {ticker}'s valuation multiple, debt costs, and capital allocation. "
            f"2) Call get_cpi(curr_date) to assess inflation trajectory and its implications for Fed policy "
            f"and {ticker}'s cost structure or pricing power. "
            f"3) Call get_real_gdp(curr_date) to gauge economic growth momentum and its effect on "
            f"{ticker}'s revenue outlook and end-market demand. "
            f"4) Call get_unemployment(curr_date) to understand labor market conditions and their impact "
            f"on consumer spending relevant to {ticker}'s customer base. "
            f"5) Call get_vix(start_date, end_date) for the past month to assess market risk appetite "
            f"and how fear/complacency levels affect {ticker}'s trading environment. "
            f"6) Call get_dxy(start_date, end_date) for the past month to understand USD strength "
            f"and its impact on {ticker}'s international revenues or input costs. "
            f"Your report MUST: "
            f"(a) Connect each macro indicator directly to {ticker} with specific reasoning. "
            f"(b) Deliver an overall macro environment verdict: Tailwind / Neutral / Headwind for {ticker}, "
            f"with a 2-3 sentence justification. "
            f"(c) Append a Markdown summary table at the end organizing each indicator, its current level, "
            f"trend, and impact on {ticker}."
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
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "macro_report": report,
        }

    return macro_analyst_node
