"""Pydantic schemas for structured output from decision nodes."""

import time
import json
import logging
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision schemas
# ---------------------------------------------------------------------------

class ResearchManagerDecision(BaseModel):
    """Research Manager output: directional decision only."""

    action: Literal["Buy", "Sell", "Hold"]
    reasoning: str = Field(description="Core reasoning for the decision")


class TraderDecision(BaseModel):
    """Trader output: execution plan with quantitative parameters."""

    action: Literal["Buy", "Sell", "Hold"]
    target_position_pct: float = Field(
        ge=0, le=100, description="Target position as percentage of total capital"
    )
    take_profit_price: Optional[float] = Field(
        default=None, description="Take-profit price; null when no position and not buying"
    )
    stop_loss_price: Optional[float] = Field(
        default=None, description="Stop-loss price; null when no position and not buying"
    )
    reasoning: str = Field(description="Explanation of the trading plan")

    @model_validator(mode="after")
    def check_sl_tp_consistency(self):
        sl, tp = self.stop_loss_price, self.take_profit_price
        if sl is not None and tp is not None and sl >= tp:
            raise ValueError(f"stop_loss_price ({sl}) must be less than take_profit_price ({tp})")
        if sl is not None and sl <= 0:
            raise ValueError(f"stop_loss_price ({sl}) must be positive")
        if tp is not None and tp <= 0:
            raise ValueError(f"take_profit_price ({tp}) must be positive")
        return self


class PortfolioManagerDecision(BaseModel):
    """Portfolio Manager output: final executable trade instruction."""

    action: Literal["Buy", "Sell", "Hold"]
    target_position_pct: float = Field(
        ge=0, le=100, description="Target position as percentage of total capital"
    )
    take_profit_price: Optional[float] = Field(
        default=None, description="Take-profit price; null when no position and not buying"
    )
    stop_loss_price: Optional[float] = Field(
        default=None, description="Stop-loss price; null when no position and not buying"
    )
    reasoning: str = Field(description="Final decision explanation")

    @model_validator(mode="after")
    def check_sl_tp_consistency(self):
        sl, tp = self.stop_loss_price, self.take_profit_price
        if sl is not None and tp is not None and sl >= tp:
            raise ValueError(f"stop_loss_price ({sl}) must be less than take_profit_price ({tp})")
        if sl is not None and sl <= 0:
            raise ValueError(f"stop_loss_price ({sl}) must be positive")
        if tp is not None and tp <= 0:
            raise ValueError(f"take_profit_price ({tp}) must be positive")
        return self


# ---------------------------------------------------------------------------
# Structured invocation helper
# ---------------------------------------------------------------------------

def invoke_structured(llm, schema: type[BaseModel], prompt: str, max_retries: int = 2):
    """Invoke an LLM with structured output, returning a validated Pydantic object.

    Uses ``llm.with_structured_output(schema, method="json_schema")`` and
    retries on validation or network errors.

    Args:
        llm: A LangChain chat model instance.
        schema: The Pydantic BaseModel class to validate against.
        prompt: The prompt string to send.
        max_retries: Number of retries on failure (default 2).

    Returns:
        An instance of *schema* with validated fields.
    """
    structured_llm = llm.with_structured_output(schema, method="json_schema")

    last_error = None
    for attempt in range(1 + max_retries):
        try:
            if attempt == 0:
                result = structured_llm.invoke(prompt)
            else:
                # Append validation feedback so the model can self-correct
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"[SYSTEM] Your previous response failed validation: {last_error}\n"
                    f"Please output a valid JSON matching the required schema."
                )
                result = structured_llm.invoke(retry_prompt)

            if result is None:
                raise ValueError("Model returned empty content")

            return result

        except Exception as e:
            last_error = str(e)
            logger.warning(
                "invoke_structured attempt %d/%d failed: %s",
                attempt + 1, 1 + max_retries, last_error,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # exponential backoff

    raise RuntimeError(
        f"invoke_structured failed after {1 + max_retries} attempts. "
        f"Last error: {last_error}"
    )
