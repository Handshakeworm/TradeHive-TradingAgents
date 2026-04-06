import json
from io import StringIO
import pandas as pd
from .alpha_vantage_common import _make_api_request


def _json_fundamentals_to_csv(raw: str, freq: str = "quarterly") -> str:
    """Convert AV fundamentals JSON response to CSV.

    AV BALANCE_SHEET/INCOME_STATEMENT/CASH_FLOW endpoints return JSON with
    annualReports and quarterlyReports arrays. This function extracts the
    appropriate array and converts to CSV for downstream pandas processing.

    If the input is already CSV (not JSON), returns it unchanged.
    """
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return raw if isinstance(raw, str) else str(raw)

    if not isinstance(data, dict):
        return raw if isinstance(raw, str) else str(raw)

    if freq.lower() == "annual":
        reports = data.get("annualReports", [])
    else:
        reports = data.get("quarterlyReports", [])

    if not reports:
        return "fiscalDateEnding\n"

    df = pd.DataFrame(reports)

    # Ensure fiscalDateEnding is first column (used by slice_csv_before)
    if "fiscalDateEnding" in df.columns:
        cols = ["fiscalDateEnding"] + [c for c in df.columns if c != "fiscalDateEnding"]
        df = df[cols]

    return df.to_csv(index=False)


def _filter_by_reported_date(csv_data: str, curr_date: str) -> str:
    """Filter CSV rows to only include reports disclosed on or before curr_date."""
    try:
        df = pd.read_csv(StringIO(csv_data))
        if 'reportedDate' in df.columns:
            df = df[pd.to_datetime(df['reportedDate']) <= pd.to_datetime(curr_date)]
            return df.to_csv(index=False)
    except Exception:
        pass
    return csv_data


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date - filters out reports disclosed after this date

    Returns:
        str: Balance sheet data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("BALANCE_SHEET", params)
    result = _json_fundamentals_to_csv(result, freq)
    if curr_date:
        result = _filter_by_reported_date(result, curr_date)
    return result


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date - filters out reports disclosed after this date

    Returns:
        str: Cash flow statement data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("CASH_FLOW", params)
    result = _json_fundamentals_to_csv(result, freq)
    if curr_date:
        result = _filter_by_reported_date(result, curr_date)
    return result


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None) -> str:
    """
    Retrieve income statement data for a given ticker symbol using Alpha Vantage.

    Args:
        ticker (str): Ticker symbol of the company
        freq (str): Reporting frequency: annual/quarterly (default quarterly) - not used for Alpha Vantage
        curr_date (str): Current date - filters out reports disclosed after this date

    Returns:
        str: Income statement data with normalized fields
    """
    params = {
        "symbol": ticker,
    }

    result = _make_api_request("INCOME_STATEMENT", params)
    result = _json_fundamentals_to_csv(result, freq)
    if curr_date:
        result = _filter_by_reported_date(result, curr_date)
    return result

