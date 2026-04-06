from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.alpha_vantage_macro import (
    get_federal_funds_rate as _get_ffr,
    get_cpi as _get_cpi,
    get_real_gdp as _get_gdp,
    get_unemployment as _get_unemployment,
    get_treasury_yield as _get_treasury_yield,
)
from tradingagents.dataflows.y_finance import get_dxy_data as _get_dxy_data
from tradingagents.dataflows.local_cache import load_cache, save_cache


def _cached_call(method_name: str, fn, *args):
    """Wrap a macro data call with local_cache."""
    cached = load_cache(method_name, args, {})
    if cached is not None:
        return cached
    result = fn(*args)
    save_cache(method_name, args, {}, result)
    return result


@tool
def get_federal_funds_rate(
    curr_date: Annotated[str, "Current trading date in yyyy-mm-dd format"],
    interval: Annotated[str, "Data interval: daily / weekly / monthly"] = "monthly",
) -> str:
    """Returns the Federal Funds Rate historical data up to curr_date.

    The Fed Funds Rate is the overnight interbank lending rate set by the FOMC.
    Rising rates increase borrowing costs, compress valuation multiples for
    growth stocks, and strengthen the USD. Falling rates ease financial conditions.
    Returns the 24 most recent data points before curr_date.
    """
    return _cached_call("get_federal_funds_rate", _get_ffr, interval, curr_date)


@tool
def get_cpi(
    curr_date: Annotated[str, "Current trading date in yyyy-mm-dd format"],
    interval: Annotated[str, "Data interval: monthly / semiannual"] = "monthly",
) -> str:
    """Returns the US Consumer Price Index (CPI) historical data up to curr_date.

    CPI measures the average change in prices paid by consumers over time.
    High/rising CPI signals inflation, pressuring the Fed to raise rates.
    This can compress margins for companies unable to pass costs to consumers.
    Returns the 24 most recent data points before curr_date.
    """
    return _cached_call("get_cpi", _get_cpi, interval, curr_date)


@tool
def get_real_gdp(
    curr_date: Annotated[str, "Current trading date in yyyy-mm-dd format"],
    interval: Annotated[str, "Data interval: annual / quarterly"] = "quarterly",
) -> str:
    """Returns US Real GDP historical data up to curr_date.

    Real GDP measures the inflation-adjusted value of all goods and services
    produced. Strong GDP growth signals a healthy economy and consumer demand.
    Slowing or negative GDP growth (recession) typically reduces revenue
    expectations for cyclical companies.
    Returns the 24 most recent data points before curr_date.
    """
    return _cached_call("get_real_gdp", _get_gdp, interval, curr_date)


@tool
def get_unemployment(
    curr_date: Annotated[str, "Current trading date in yyyy-mm-dd format"],
) -> str:
    """Returns the US Unemployment Rate historical data up to curr_date (monthly).

    The unemployment rate reflects labor market health. Low unemployment
    supports consumer spending power; high unemployment signals economic
    weakness and reduced demand for consumer-facing businesses.
    Returns the 24 most recent data points before curr_date.
    """
    return _cached_call("get_unemployment", _get_unemployment, curr_date)


@tool
def get_treasury_yield(
    curr_date: Annotated[str, "Current trading date in yyyy-mm-dd format"],
    maturity: Annotated[str, "Bond maturity: 3month / 2year / 5year / 7year / 10year / 30year"] = "10year",
    interval: Annotated[str, "Data interval: daily / weekly / monthly"] = "monthly",
) -> str:
    """Returns US Treasury Yield historical data up to curr_date.

    The 10-year yield is the benchmark risk-free rate used to discount future
    cash flows. An inverted yield curve (short-term > long-term) historically
    signals recession risk within 12-18 months. Rising long-term yields
    pressure high-P/E growth stocks by increasing the discount rate.
    Returns the 24 most recent data points before curr_date.
    """
    return _cached_call("get_treasury_yield", _get_treasury_yield, interval, maturity, curr_date)


@tool
def get_dxy(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Returns US Dollar Index (DXY) daily data for the given date range.

    DXY tracks the USD against a basket of major currencies (EUR, JPY, GBP,
    CAD, SEK, CHF). A strong USD (DXY > 100) is a headwind for US companies
    with significant overseas revenues (e.g., tech multinationals) as it
    reduces the USD value of foreign earnings. A weak USD is a tailwind.
    """
    return _get_dxy_data(start_date, end_date)
