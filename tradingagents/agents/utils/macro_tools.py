from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_macro_indicator(
    series_id: Annotated[
        str,
        "FRED series ID, e.g. 'FEDFUNDS' (Fed Funds Rate), 'CPIAUCSL' (CPI), "
        "'UNRATE' (Unemployment), 'VIXCLS' (VIX), 'GS10' (10Y Treasury Yield)",
    ],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve a macroeconomic indicator time series from FRED
    (Federal Reserve Economic Data). Requires FRED_API_KEY in environment.
    Common series: FEDFUNDS, CPIAUCSL, UNRATE, VIXCLS, GS10, GS2, T10Y2Y,
    PAYEMS (nonfarm payrolls), GDP, DEXUSEU (USD/EUR).
    Args:
        series_id: FRED series identifier
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        CSV-formatted time series with date and value columns
    """
    return route_to_vendor("get_macro_indicator", series_id, start_date, end_date)


@tool
def get_macro_snapshot(
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    lookback_days: Annotated[int, "Days to look back for latest values"] = 90,
) -> str:
    """
    Get a macro economic snapshot for a reference date, showing the most
    recently available values of key indicators: Fed Funds Rate, CPI,
    Unemployment Rate, VIX, 10Y Treasury Yield, 2Y Yield, and 10Y-2Y spread.
    Requires FRED_API_KEY in environment.
    Args:
        date: Reference date in yyyy-mm-dd format
        lookback_days: How many days back to look for latest values (default 90)
    Returns:
        Formatted table of key macro indicators
    """
    return route_to_vendor("get_macro_snapshot", date, lookback_days)


@tool
def list_available_macro_series() -> str:
    """
    List all available FRED macro indicator series IDs and their descriptions.
    Use this to discover which series_id to pass to get_macro_indicator.
    Returns:
        Formatted list of series ID and description pairs
    """
    return route_to_vendor("list_available_macro_series")
