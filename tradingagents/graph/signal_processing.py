# TradingAgents/graph/signal_processing.py

import json

from langchain_openai import ChatOpenAI


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for fallback processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Attempts JSON parsing first (structured output from Portfolio Manager),
        falls back to LLM extraction for legacy free-text signals.

        Args:
            full_signal: Complete trading signal (JSON string or free text)

        Returns:
            Extracted action: BUY, SELL, or HOLD
        """
        # Try structured JSON parsing first
        try:
            decision = json.loads(full_signal)
            action = decision.get("action", "").upper()
            if action in ("BUY", "SELL", "HOLD"):
                return action
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        # Fallback: use LLM to extract from free text
        messages = [
            (
                "system",
                "You are an efficient assistant that extracts the trading decision from analyst reports. "
                "Extract the rating as exactly one of: BUY, HOLD, SELL. "
                "Output only the single rating word, nothing else.",
            ),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content
