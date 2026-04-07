"""Position tracking for backtesting."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class PositionTracker:
    """Tracks a single-instrument position through a backtest.

    All monetary amounts are in the same currency as the stock price.
    """

    initial_capital: float
    cash: float = field(init=False)
    shares: float = 0.0
    avg_cost: float = 0.0
    current_stop_loss: Optional[float] = None
    current_take_profit: Optional[float] = None
    last_action: str = "Hold"

    def __post_init__(self):
        self.cash = self.initial_capital

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_total_value(self, price: float) -> float:
        """Total account value at a given price."""
        return self.cash + self.shares * price

    def get_position_pct(self, price: float) -> float:
        """Current position as percentage of total capital."""
        total = self.get_total_value(price)
        if total <= 0:
            return 0.0
        return (self.shares * price / total) * 100

    def get_unrealized_pnl_pct(self, price: float) -> float:
        """Unrealized PnL as a percentage of cost basis."""
        if self.shares <= 0 or self.avg_cost <= 0:
            return 0.0
        return ((price - self.avg_cost) / self.avg_cost) * 100

    def get_state_dict(self, close_price: float) -> Dict[str, Any]:
        """Export position state for injection into agent state."""
        return {
            "current_position_pct": self.get_position_pct(close_price),
            "avg_cost": self.avg_cost,
            "total_capital": self.get_total_value(close_price),
            "current_stop_loss": self.current_stop_loss,
            "current_take_profit": self.current_take_profit,
            "last_action": self.last_action,
            "unrealized_pnl_pct": self.get_unrealized_pnl_pct(close_price),
        }

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def execute_order(
        self,
        target_position_pct: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        action: str = "Hold",
    ) -> Dict[str, Any]:
        """Execute an order to reach *target_position_pct* at *price*.

        Returns a dict describing what happened.
        """
        total_value = self.get_total_value(price)
        target_value = total_value * (target_position_pct / 100.0)
        current_value = self.shares * price
        delta_value = target_value - current_value

        result = {"action": action, "price": price, "shares_traded": 0.0, "cost": 0.0}

        if delta_value > 0:
            # Buy
            shares_to_buy = math.floor(delta_value / price)
            if shares_to_buy > 0:
                cost = shares_to_buy * price
                if cost <= self.cash:
                    # Update average cost
                    total_shares = self.shares + shares_to_buy
                    if total_shares > 0:
                        self.avg_cost = (
                            (self.avg_cost * self.shares + cost) / total_shares
                        )
                    self.shares = total_shares
                    self.cash -= cost
                    result["shares_traded"] = shares_to_buy
                    result["cost"] = cost
                    self.last_action = "Buy"
        elif delta_value < 0:
            # Sell
            shares_to_sell = min(
                math.floor(abs(delta_value) / price), self.shares
            )
            if shares_to_sell > 0:
                proceeds = shares_to_sell * price
                self.shares -= shares_to_sell
                self.cash += proceeds
                result["shares_traded"] = -shares_to_sell
                result["cost"] = -proceeds
                self.last_action = "Sell"
                # Reset avg_cost if fully exited
                if self.shares <= 0:
                    self.shares = 0
                    self.avg_cost = 0.0
        else:
            self.last_action = "Hold"

        # Update stop/take-profit with sanity check:
        # stop-loss must be below current price, take-profit must be above
        if stop_loss is not None and stop_loss < price:
            self.current_stop_loss = stop_loss
        else:
            self.current_stop_loss = None
        if take_profit is not None and take_profit > price:
            self.current_take_profit = take_profit
        else:
            self.current_take_profit = None

        return result

    def check_stop_take(self, high: float, low: float) -> Optional[Dict[str, Any]]:
        """Check if stop-loss or take-profit triggers within a day's range.

        Returns a dict with trigger info, or None if not triggered.
        Stop-loss takes priority (conservative assumption).
        """
        if self.shares <= 0:
            return None

        # Stop-loss check (priority)
        if self.current_stop_loss is not None and low <= self.current_stop_loss:
            trigger_price = self.current_stop_loss
            return self._close_position(trigger_price, "stop_loss")

        # Take-profit check
        if self.current_take_profit is not None and high >= self.current_take_profit:
            trigger_price = self.current_take_profit
            return self._close_position(trigger_price, "take_profit")

        return None

    def _close_position(self, price: float, reason: str) -> Dict[str, Any]:
        """Close the entire position at *price*."""
        proceeds = self.shares * price
        shares_sold = self.shares
        pnl = (price - self.avg_cost) * shares_sold

        self.cash += proceeds
        self.shares = 0
        self.avg_cost = 0.0
        self.current_stop_loss = None
        self.current_take_profit = None
        self.last_action = "Sell"

        return {
            "reason": reason,
            "price": price,
            "shares_sold": shares_sold,
            "proceeds": proceeds,
            "realized_pnl": pnl,
        }
