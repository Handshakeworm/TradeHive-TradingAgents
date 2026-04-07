"""Backtesting engine: daily loop over historical data."""

from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .position import PositionTracker

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Run a daily backtesting loop using TradingAgentsGraph.

    OHLC data is read from the project's bulk cache (data_cache/bulk/{TICKER}/stock_data.csv),
    which is already populated by the bulk prefetch mechanism. No extra API calls needed.

    Usage::

        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.backtesting import BacktestEngine

        ta = TradingAgentsGraph(...)
        engine = BacktestEngine(ta, initial_capital=100_000)
        results = engine.run("NVDA", "2024-01-02", "2024-03-29")
    """

    def __init__(
        self,
        graph: Any,  # TradingAgentsGraph (avoid circular import)
        initial_capital: float = 100_000,
        results_dir: str = "backtest_results",
    ):
        self.graph = graph
        self.initial_capital = initial_capital
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Execute the backtest over [start_date, end_date].

        Args:
            ticker: Stock ticker symbol.
            start_date: First trading day (inclusive), yyyy-mm-dd.
            end_date: Last trading day (inclusive), yyyy-mm-dd.

        Returns:
            Dict with daily_log, final_value, total_return_pct, etc.
        """
        ohlc = self._load_ohlc(ticker, start_date, end_date)
        if ohlc.empty:
            raise ValueError(
                f"No OHLC data for {ticker} in [{start_date}, {end_date}]. "
                "Make sure bulk cache is populated (run pull_cache.py first)."
            )

        trading_days = ohlc.index.tolist()
        logger.info(
            "Backtest %s: %d trading days from %s to %s",
            ticker, len(trading_days), trading_days[0], trading_days[-1],
        )

        position = PositionTracker(initial_capital=self.initial_capital)
        pending_decision: Optional[Dict] = None
        daily_log: List[Dict[str, Any]] = []

        for i, day_str in enumerate(trading_days):
            row = ohlc.loc[day_str]
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])

            day_record = {
                "date": day_str,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            # ----------------------------------------------------------
            # 1. Open: execute previous day's PM decision
            # ----------------------------------------------------------
            if pending_decision is not None:
                order_result = position.execute_order(
                    target_position_pct=pending_decision.get("target_position_pct", 0),
                    price=open_price,
                    stop_loss=pending_decision.get("stop_loss_price"),
                    take_profit=pending_decision.get("take_profit_price"),
                    action=pending_decision.get("action", "Hold"),
                )
                day_record["order"] = order_result
                logger.info(
                    "Day %s open: executed %s @ %.2f, shares_traded=%s",
                    day_str, order_result["action"], open_price,
                    order_result["shares_traded"],
                )

            # ----------------------------------------------------------
            # 2. Intraday: check stop-loss / take-profit
            # ----------------------------------------------------------
            trigger = position.check_stop_take(high_price, low_price)
            if trigger is not None:
                day_record["trigger"] = trigger
                logger.info(
                    "Day %s: %s triggered @ %.2f, PnL=%.2f",
                    day_str, trigger["reason"], trigger["price"],
                    trigger["realized_pnl"],
                )

            # ----------------------------------------------------------
            # 3. Close: update position, run pipeline
            # ----------------------------------------------------------
            pos_state = position.get_state_dict(close_price)
            day_record["position"] = pos_state.copy()
            day_record["total_value"] = position.get_total_value(close_price)

            # Run full agent pipeline
            try:
                final_state, decision_str = self.graph.propagate(
                    ticker, day_str, position_state=pos_state,
                )

                # Parse PM's structured output
                try:
                    pending_decision = json.loads(
                        final_state["final_trade_decision"]
                    )
                except (json.JSONDecodeError, TypeError):
                    pending_decision = {"action": decision_str, "target_position_pct": 0}

                day_record["decision"] = pending_decision
                logger.info(
                    "Day %s close: PM decision=%s, target_pct=%.1f%%",
                    day_str,
                    pending_decision.get("action"),
                    pending_decision.get("target_position_pct", 0),
                )

            except Exception as e:
                logger.error("Day %s: pipeline failed: %s", day_str, e)
                day_record["error"] = str(e)
                pending_decision = None

            daily_log.append(day_record)

        # ----------------------------------------------------------
        # Summary
        # ----------------------------------------------------------
        last_close = float(ohlc.iloc[-1]["close"])
        final_value = position.get_total_value(last_close)
        total_return_pct = (
            (final_value - self.initial_capital) / self.initial_capital * 100
        )

        results = {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return_pct": total_return_pct,
            "trading_days": len(trading_days),
            "daily_log": daily_log,
        }

        # Save results
        out_path = self.results_dir / f"{ticker}_{start_date}_{end_date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(
            "Backtest complete: %s %.2f%% return, saved to %s",
            ticker, total_return_pct, out_path,
        )

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_ohlc(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Load daily OHLC from bulk cache and slice to [start_date, end_date]."""
        from tradingagents.dataflows.bulk_cache import bulk_has, bulk_load

        if not bulk_has(ticker, "stock_data"):
            logger.warning("Bulk cache not found for %s, attempting to fetch...", ticker)
            # Trigger a single get_stock_data call which will populate bulk cache
            from tradingagents.dataflows.interface import route_to_vendor
            route_to_vendor("get_stock_data", ticker, start_date, end_date)

            if not bulk_has(ticker, "stock_data"):
                return pd.DataFrame()

        csv_text = bulk_load(ticker, "stock_data")

        df = pd.read_csv(StringIO(csv_text))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        # Filter to date range
        mask = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)
        df = df.loc[mask].copy()

        # Use date string as index for easy lookup
        df.index = df["timestamp"].dt.strftime("%Y-%m-%d")
        df.index.name = "date"

        return df
