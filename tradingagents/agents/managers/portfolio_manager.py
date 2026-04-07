import json

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import (
    PortfolioManagerDecision,
    invoke_structured,
)


def create_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]

        # Trader's quantitative plan
        trader_plan_raw = state["trader_investment_plan"]
        try:
            trader_plan = json.loads(trader_plan_raw)
        except (json.JSONDecodeError, TypeError):
            trader_plan = {"action": "Hold", "target_position_pct": 0, "reasoning": trader_plan_raw}

        # Position context
        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        total_capital = state.get("total_capital", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        last_action = state.get("last_action", "Hold")

        # Past memories
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""As the Portfolio Manager, you make the final trading decision. Synthesize the risk analysts' debate and the Trader's proposed plan into a definitive, executable instruction.

{instrument_context}

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'Hold')}
- Target position: {trader_plan.get('target_position_pct', 0)}% of capital
- Take-profit: {trader_plan.get('take_profit_price', 'None')}
- Stop-loss: {trader_plan.get('stop_loss_price', 'None')}
- Reasoning: {trader_plan.get('reasoning', 'N/A')}

**Current Position:**
- Position: {position_pct:.1f}% of capital (${total_capital:,.0f} total)
- Average cost: ${avg_cost:.2f}
- Unrealized PnL: {unrealized_pnl:.1f}%
- Last action: {last_action}

**Your task — deliver the final parameters:**
1. **action**: Buy, Sell, or Hold
2. **target_position_pct**: Final target position percentage (may differ from Trader's proposal based on risk debate)
3. **take_profit_price**: Final take-profit level (null if no position)
4. **stop_loss_price**: Final stop-loss level (null if no position)

Consider the risk analysts' arguments carefully. If they raised valid concerns about the Trader's parameters, adjust accordingly.

**Past decision lessons:**
"{past_memory_str}"

**Risk Analysts Debate History:**
{history}

Be decisive. Ground every conclusion in specific evidence from the analysts."""

        decision = invoke_structured(llm, PortfolioManagerDecision, prompt)

        decision_json = decision.model_dump_json()

        new_risk_debate_state = {
            "judge_decision": decision_json,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": decision_json,
        }

    return portfolio_manager_node
