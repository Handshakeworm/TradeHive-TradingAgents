"""
CoinGecko 加密货币数据模块
- 完全免费，无需 API Key（公共端点 rate limit: ~10-30 req/min）
- 支持实时价格与历史 OHLCV
- 分工说明：本模块只做数据采集与格式化，不做向量化（向量化归 #3）
"""

from typing import Annotated
from datetime import datetime, timedelta
import time
import requests
import pandas as pd

# CoinGecko 公共 API Base URL（无需 API Key）
_CG_BASE = "https://api.coingecko.com/api/v3"

# 常用 Ticker -> CoinGecko ID 映射（可按需扩充）
CRYPTO_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "ATOM": "cosmos",
    "NEAR": "near",
}


def _cg_get(endpoint: str, params: dict = None, retries: int = 3) -> dict | list:
    """带重试的 CoinGecko GET 请求。"""
    url = f"{_CG_BASE}{endpoint}"
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:  # Rate limit
                time.sleep(60)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise RuntimeError(f"CoinGecko API error: {e}") from e
            time.sleep(2 ** attempt)
    return {}


def _resolve_coin_id(symbol: str) -> str:
    """将 BTC / ETH 等 ticker 转换为 CoinGecko coin_id。"""
    upper = symbol.upper().replace("-USD", "").replace("USDT", "").replace("/USD", "")
    return CRYPTO_ID_MAP.get(upper, upper.lower())


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数（供 interface.py 注册为 Agent 可调用工具）
# ─────────────────────────────────────────────────────────────────────────────

def get_crypto_price(
    symbol: Annotated[str, "Crypto ticker symbol, e.g. BTC, ETH, SOL"],
    currency: Annotated[str, "Quote currency, default usd"] = "usd",
) -> str:
    """
    获取加密货币实时价格及市场概览（当前时刻快照）。
    返回格式化字符串，供 Agent 直接阅读。
    """
    coin_id = _resolve_coin_id(symbol)
    try:
        data = _cg_get(
            f"/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "false",
                "developer_data": "false",
            },
        )
        market = data.get("market_data", {})
        cur = currency.lower()
        price = market.get("current_price", {}).get(cur, "N/A")
        mktcap = market.get("market_cap", {}).get(cur, "N/A")
        vol_24h = market.get("total_volume", {}).get(cur, "N/A")
        chg_24h = market.get("price_change_percentage_24h", "N/A")
        chg_7d = market.get("price_change_percentage_7d", "N/A")
        chg_30d = market.get("price_change_percentage_30d", "N/A")
        high_24h = market.get("high_24h", {}).get(cur, "N/A")
        low_24h = market.get("low_24h", {}).get(cur, "N/A")
        supply = market.get("circulating_supply", "N/A")
        ath = market.get("ath", {}).get(cur, "N/A")
        ath_date = market.get("ath_date", {}).get(cur, "N/A")

        result = (
            f"# Crypto Market Snapshot: {symbol.upper()} ({coin_id})\n"
            f"# Quote currency: {cur.upper()}\n"
            f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"Current Price:          {price:,.4f} {cur.upper()}\n"
            f"24h High / Low:         {high_24h:,.4f} / {low_24h:,.4f}\n"
            f"24h Price Change:       {chg_24h:.2f}%\n"
            f"7d Price Change:        {chg_7d:.2f}%\n"
            f"30d Price Change:       {chg_30d:.2f}%\n"
            f"Market Cap:             {mktcap:,.0f} {cur.upper()}\n"
            f"24h Volume:             {vol_24h:,.0f} {cur.upper()}\n"
            f"Circulating Supply:     {supply:,.0f} {symbol.upper()}\n"
            f"All-Time High:          {ath:,.4f} {cur.upper()} (on {ath_date[:10] if ath_date else 'N/A'})\n"
        )
        return result
    except Exception as e:
        return f"Error fetching crypto price for {symbol}: {e}"


def get_crypto_historical(
    symbol: Annotated[str, "Crypto ticker symbol, e.g. BTC, ETH"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    currency: Annotated[str, "Quote currency, default usd"] = "usd",
) -> str:
    """
    获取加密货币历史 OHLCV 数据（日线）。
    策略：优先 yfinance（支持完整历史，如 BTC-USD），
    失败时降级到 CoinGecko 免费端点（仅支持最近 365 天）。
    数据格式与 yfinance 股票数据保持一致（CSV with header）。
    同时写入本地缓存（parquet），供 #3 向量化直接读取。
    """
    # 先尝试 yfinance（BTC-USD 格式，历史完整）
    yf_symbol = _to_yfinance_symbol(symbol, currency)
    try:
        import yfinance as yf
        ticker = yf.Ticker(yf_symbol)
        data = ticker.history(start=start_date, end=end_date)
        if not data.empty:
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            df = data.reset_index()
            df.columns = [c.lower() for c in df.columns]
            # 统一列名：date, open, high, low, close, volume
            if "date" not in df.columns and "datetime" in df.columns:
                df = df.rename(columns={"datetime": "date"})
            df["date"] = df["date"].astype(str).str[:10]
            keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
            df = df[keep].dropna().reset_index(drop=True)

            _save_to_cache(df, symbol, "crypto", start_date, end_date)

            csv_str = df.to_csv(index=False)
            header = (
                f"# Crypto historical data: {symbol.upper()} (via yfinance: {yf_symbol})\n"
                f"# Date range: {start_date} to {end_date}\n"
                f"# Quote currency: {currency.upper()}\n"
                f"# Records: {len(df)}\n\n"
            )
            return header + csv_str
    except Exception:
        pass  # 降级到 CoinGecko

    # 降级：CoinGecko 免费端点（仅支持最近 365 天）
    coin_id = _resolve_coin_id(symbol)
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        days_from_now = (datetime.utcnow() - start_dt).days + 1
        if days_from_now > 365:
            return (
                f"# Crypto historical data: {symbol.upper()}\n"
                f"# Date range: {start_date} to {end_date}\n"
                f"# Source: CoinGecko free API\n\n"
                f"Error: Requested date range is more than 365 days ago. "
                f"CoinGecko free API only supports {symbol.upper()} history up to 365 days back. "
                f"Try using a ticker like '{yf_symbol}' directly with yfinance for older data."
            )
        days_param = min(days_from_now, 365)
        data = _cg_get(
            f"/coins/{coin_id}/market_chart",
            params={"vs_currency": currency, "days": days_param, "interval": "daily"},
        )
        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        market_caps = data.get("market_caps", [])

        if not prices:
            return f"No historical data for {symbol} between {start_date} and {end_date}"

        df = pd.DataFrame(prices, columns=["timestamp", "close"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime("%Y-%m-%d")
        df["volume"] = [v[1] for v in volumes[: len(df)]]
        df["market_cap"] = [m[1] for m in market_caps[: len(df)]]
        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]
        df = df[["date", "open", "high", "low", "close", "volume", "market_cap"]]
        df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)

        _save_to_cache(df, symbol, "crypto", start_date, end_date)

        csv_str = df.to_csv(index=False)
        header = (
            f"# Crypto historical data: {symbol.upper()} ({coin_id})\n"
            f"# Date range: {start_date} to {end_date}\n"
            f"# Quote currency: {currency.upper()}\n"
            f"# Records: {len(df)}\n\n"
        )
        return header + csv_str
    except Exception as e:
        return f"Error fetching historical crypto data for {symbol}: {e}"


def _to_yfinance_symbol(symbol: str, currency: str = "usd") -> str:
    """将 BTC/ETH 等转换为 yfinance 格式（BTC-USD）。"""
    upper = symbol.upper().replace("-USD", "").replace("USDT", "").replace("/USD", "")
    cur = currency.upper()
    return f"{upper}-{cur}"


def get_crypto_market_overview(
    top_n: Annotated[int, "Number of top coins by market cap to fetch"] = 10,
    currency: Annotated[str, "Quote currency, default usd"] = "usd",
) -> str:
    """
    获取加密货币市场总览（市值前 N 名）。
    适合宏观情绪判断，供 Agent 了解整体市场状态。
    """
    try:
        data = _cg_get(
            "/coins/markets",
            params={
                "vs_currency": currency,
                "order": "market_cap_desc",
                "per_page": top_n,
                "page": 1,
                "sparkline": "false",
            },
        )
        if not data:
            return "No market overview data available."

        lines = [
            f"# Crypto Market Overview (Top {top_n} by Market Cap)",
            f"# Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"# Quote currency: {currency.upper()}\n",
            f"{'Rank':<5} {'Symbol':<8} {'Name':<20} {'Price':>12} {'24h%':>8} {'Market Cap':>18} {'Volume 24h':>18}",
            "-" * 90,
        ]
        for coin in data:
            rank = coin.get("market_cap_rank", "-")
            sym = coin.get("symbol", "").upper()
            name = coin.get("name", "")[:18]
            price = coin.get("current_price", 0)
            chg = coin.get("price_change_percentage_24h") or 0
            mcap = coin.get("market_cap", 0)
            vol = coin.get("total_volume", 0)
            lines.append(
                f"{rank:<5} {sym:<8} {name:<20} {price:>12,.4f} {chg:>7.2f}% {mcap:>18,.0f} {vol:>18,.0f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching crypto market overview: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 内部工具：本地缓存（供 #3 RAP 向量库读取，不做向量化）
# ─────────────────────────────────────────────────────────────────────────────

def _save_to_cache(df: pd.DataFrame, symbol: str, category: str, start: str, end: str):
    """将 DataFrame 写入本地 parquet 缓存，目录结构：data_cache/{category}/{symbol}/。"""
    try:
        from .local_cache import save_dataframe
        save_dataframe(df, symbol, category, start, end)
    except Exception:
        pass  # 缓存失败不影响主流程
