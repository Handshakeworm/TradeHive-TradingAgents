import json

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.schemas import TraderDecision, invoke_structured


def create_trader(llm, memory):
    def trader_node(state) -> dict:
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)

        # Research Manager's directional decision
        investment_plan = state["investment_plan"]
        try:
            rm_decision = json.loads(investment_plan)
        except (json.JSONDecodeError, TypeError):
            rm_decision = {"action": "Hold", "reasoning": investment_plan}

        # Reports
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # Position context
        position_pct = state.get("current_position_pct", 0)
        avg_cost = state.get("avg_cost", 0)
        total_capital = state.get("total_capital", 0)
        unrealized_pnl = state.get("unrealized_pnl_pct", 0)
        current_stop_loss = state.get("current_stop_loss")
        current_take_profit = state.get("current_take_profit")
        last_action = state.get("last_action", "Hold")

        # Past memories
        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        prompt = f"""You are the Execution Planner (Trader). The Research Manager has made a directional decision. Your job is to translate that direction into a concrete, quantitative trading plan.

{instrument_context}

**Research Manager's Decision:**
- Action: {rm_decision.get('action', 'Hold')}
- Reasoning: {rm_decision.get('reasoning', 'N/A')}

**Current Position:**
- Position: {position_pct:.1f}% of capital (${total_capital:,.0f} total)
- Average cost: ${avg_cost:.2f}
- Unrealized PnL: {unrealized_pnl:.1f}%
- Current stop-loss: {current_stop_loss or 'None'}
- Current take-profit: {current_take_profit or 'None'}
- Last action: {last_action}

**Your task — output these specific parameters:**
1. **target_position_pct**: What percentage of total capital should be allocated to this position? (0 = fully exit, 100 = all-in)
2. **take_profit_price**: At what price should we take profits? (null if no position after this action)
3. **stop_loss_price**: At what price should we cut losses? (null if no position after this action)

Use the analyst reports below and past trading lessons to determine appropriate levels.

**Market Research Report:**
{market_research_report}

**Sentiment Report:**
{sentiment_report}

**News Report:**
{news_report}

**Fundamentals Report:**
{fundamentals_report}

**Past trading lessons:**
{past_memory_str}

Be precise with price levels. Base stop-loss and take-profit on technical support/resistance levels from the market report when available."""

        decision = invoke_structured(llm, TraderDecision, prompt)

        decision_json = decision.model_dump_json()

        return {
            "messages": [],
            "trader_investment_plan": decision_json,
            "sender": "Trader",
        }

    return trader_node
