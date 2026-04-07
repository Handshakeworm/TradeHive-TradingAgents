import json

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import (
    ResearchManagerDecision,
    invoke_structured,
)


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        # Position context
        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        last_action = state.get("last_action", "Hold")

        # Retrieve past memories
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""As the Research Manager and debate facilitator, critically evaluate this round of bull vs bear debate and make a decisive directional call.

Your task is simple: decide Buy, Sell, or Hold. Do NOT create a detailed investment plan — that is the Trader's job. Focus only on the direction and your core reasoning.

- Align with the bull analyst, the bear analyst, or choose Hold only if strongly justified.
- Avoid defaulting to Hold simply because both sides have valid points — commit to a stance.
- Take into account your past mistakes on similar situations.

{instrument_context}

Current position: {position_pct:.1f}% of capital | Avg cost: {avg_cost:.2f} | Unrealized PnL: {unrealized_pnl:.1f}% | Last action: {last_action}

Past reflections on mistakes:
"{past_memory_str}"

Debate History:
{history}"""

        decision = invoke_structured(llm, ResearchManagerDecision, prompt)

        decision_json = decision.model_dump_json()

        new_investment_debate_state = {
            "judge_decision": decision_json,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": decision_json,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": decision_json,
        }

    return research_manager_node
