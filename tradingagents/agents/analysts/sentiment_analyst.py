from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_news
from tradingagents.agents.utils.sentiment_tools import get_sentiment_summary, get_vix
from tradingagents.dataflows.config import get_config


def create_sentiment_analyst(llm):
    def sentiment_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_sentiment_summary,
            get_vix,
        ]

        system_message = (
            "You are a sentiment analyst tasked with quantifying and interpreting market sentiment for a specific company. "
            "Your workflow: "
            "1) Call get_sentiment_summary(ticker, start_date, end_date) first to get a daily aggregated sentiment table — this shows average sentiment scores, bullish/neutral/bearish article counts per day, and the overall period average. "
            "2) Call get_vix(start_date, end_date) to get the VIX volatility index as macroeconomic fear/greed context for the same period. "
            "3) Call get_news(ticker, start_date, end_date) to retrieve the underlying news articles and identify key sentiment drivers (major events, earnings, product launches, controversies). "
            "Your report must include: a quantitative sentiment trend section (referencing the daily scores from get_sentiment_summary), VIX context (whether market fear elevated or suppressed sentiment), identification of key sentiment-shifting events with dates, and an overall sentiment verdict. "
            "Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
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
            "sentiment_report": report,
        }

    return sentiment_analyst_node
