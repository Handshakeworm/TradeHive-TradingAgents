from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.news_data_tools import get_news
from tradingagents.agents.utils.sentiment_tools import get_news_sentiment, get_reddit_sentiment


def create_sentiment_analyst(llm):
    """
    Sentiment Analyst Agent — quantitative sentiment scoring layer.

    Differences from social_media_analyst (qualitative baseline):
    - Calls get_news_sentiment() to obtain VADER compound scores per article
    - Calls get_reddit_sentiment() for social media signal (if credentials configured)
    - Outputs structured sentiment summary: POSITIVE/NEUTRAL/NEGATIVE breakdown,
      aggregate compound score, trend direction, and 5-point risk flag
    - Writes to state["sentiment_report"] (replaces or augments social analyst)
    """

    def sentiment_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_news_sentiment,
            get_reddit_sentiment,
        ]

        system_message = (
            "You are a quantitative sentiment analyst specializing in market sentiment "
            "measurement for stocks and crypto assets. "
            "Your job is to produce a structured, data-driven sentiment report by:\n"
            "1. Calling get_news_sentiment() to retrieve VADER-scored news articles "
            "(compound score: -1 = very negative, +1 = very positive, threshold ±0.05).\n"
            "2. Optionally calling get_reddit_sentiment() for social media signal.\n"
            "3. Calling get_news() for qualitative context on major headlines.\n\n"
            "Structure your final report with the following sections:\n"
            "- **Sentiment Summary**: Overall label (POSITIVE/NEUTRAL/NEGATIVE), "
            "aggregate compound score, article count breakdown\n"
            "- **Trend Analysis**: Is sentiment improving, deteriorating, or stable? "
            "Cite specific dates or events\n"
            "- **Key Drivers**: Top 3 positive and top 3 negative catalysts found in news\n"
            "- **Risk Flag** (1–5 scale): 1 = very bullish sentiment, 5 = very bearish sentiment\n"
            "- **Markdown Table**: Summary of top 10 articles with date, title, and sentiment score\n\n"
            "Be objective and data-driven. Quote compound scores directly in your analysis."
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
            "sentiment_report": report,
        }

    return sentiment_analyst_node
