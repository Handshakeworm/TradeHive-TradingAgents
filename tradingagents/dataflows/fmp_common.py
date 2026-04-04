import os
import json
import requests


FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


class FMPRateLimitError(Exception):
    """Exception raised when FMP API rate limit is exceeded."""
    pass


def get_fmp_api_key() -> str:
    """Retrieve the API key for Financial Modeling Prep from environment variables."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError("FMP_API_KEY environment variable is not set.")
    return api_key


def fmp_api_request(endpoint: str, params: dict = None) -> dict | list:
    """Make a request to the FMP API and return the JSON response.

    Args:
        endpoint: API endpoint path (e.g., "/key-metrics/AAPL")
        params: Optional query parameters

    Returns:
        Parsed JSON response (dict or list)

    Raises:
        FMPRateLimitError: When API rate limit is exceeded
    """
    url = f"{FMP_BASE_URL}{endpoint}"

    api_params = params.copy() if params else {}
    api_params["apikey"] = get_fmp_api_key()

    response = requests.get(url, params=api_params)
    response.raise_for_status()

    data = response.json()

    # FMP returns an error message dict when rate limited
    if isinstance(data, dict) and "Error Message" in data:
        msg = data["Error Message"]
        if "limit" in msg.lower():
            raise FMPRateLimitError(f"FMP rate limit exceeded: {msg}")
        raise ValueError(f"FMP API error: {msg}")

    return data
