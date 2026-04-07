# TradingAgents/graph/propagation.py

from typing import Dict, Any, List, Optional
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=200):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    # Default empty-position state for when no position data is provided
    _DEFAULT_POSITION = {
        "current_position_pct": 0.0,
        "avg_cost": 0.0,
        "total_capital": 0.0,
        "current_stop_loss": None,
        "current_take_profit": None,
        "last_action": "Hold",
        "unrealized_pnl_pct": 0.0,
    }

    def create_initial_state(
        self,
        company_name: str,
        trade_date: str,
        position_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph.

        Args:
            company_name: Ticker or company name to analyse.
            trade_date: Trading date string.
            position_state: Optional dict with position-tracking fields
                (current_position_pct, avg_cost, total_capital, etc.).
                If *None*, defaults to an empty-position state.
        """
        pos = {**self._DEFAULT_POSITION, **(position_state or {})}

        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "investment_debate_state": InvestDebateState(
                {
                    "bull_history": "",
                    "bear_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "history": "",
                    "latest_speaker": "",
                    "current_aggressive_response": "",
                    "current_conservative_response": "",
                    "current_neutral_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "macro_report": "",
            # position tracking
            **pos,
        }

    def get_graph_args(self, callbacks: Optional[List] = None) -> Dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            callbacks: Optional list of callback handlers for tool execution tracking.
                       Note: LLM callbacks are handled separately via LLM constructor.
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
