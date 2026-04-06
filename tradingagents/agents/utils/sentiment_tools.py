from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.sentiment_utils import get_sentiment_summary as _get_sentiment_summary
from tradingagents.dataflows.y_finance import get_vix_data as _get_vix_data


@tool
def get_sentiment_summary(
    ticker: Annotated[str, "Stock ticker symbol, e.g. 'NVDA'"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Returns a daily aggregated sentiment summary for a stock ticker based on
    Alpha Vantage NEWS_SENTIMENT data cached locally.

    For each day in the range, reports:
    - Average ticker-specific sentiment score (-1 to +1)
    - Sentiment label (Bullish / Somewhat-Bullish / Neutral / Somewhat-Bearish / Bearish)
    - Count of Bullish, Neutral, and Bearish articles
    - Total article count

    Use this tool to quantify how market sentiment toward a stock has evolved
    over the analysis period, complementing the qualitative news analysis.
    """
    return _get_sentiment_summary(ticker, start_date, end_date)


@tool
def get_vix(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Returns daily VIX (CBOE Volatility Index) data for the given date range.

    VIX reflects the market's expectation of 30-day S&P 500 volatility and is
    widely used as a proxy for overall market fear and uncertainty.
    Use this tool to provide macroeconomic sentiment context alongside
    company-specific sentiment analysis.
    """
    return _get_vix_data(start_date, end_date)
