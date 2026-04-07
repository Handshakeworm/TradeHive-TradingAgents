import json


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # Parse Trader's quantitative plan
        trader_plan_raw = state["trader_investment_plan"]
        try:
            trader_plan = json.loads(trader_plan_raw)
        except (json.JSONDecodeError, TypeError):
            trader_plan = {}

        count = risk_debate_state.get("count", 0)

        if count == 0:
            data_context = f"""Use insights from the following data sources to support a balanced strategy:

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}"""
        else:
            data_context = "Use the debate history to support a balanced strategy."

        prompt = f"""As the Neutral Risk Analyst, your role is to provide a balanced perspective on the Trader's plan. Evaluate whether the proposed parameters strike the right balance between risk and reward.

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'N/A')}
- Target position: {trader_plan.get('target_position_pct', 'N/A')}% of capital
- Take-profit: {trader_plan.get('take_profit_price', 'N/A')}
- Stop-loss: {trader_plan.get('stop_loss_price', 'N/A')}

**Your stance — argue for balanced parameters:**
- Position size: evaluate if it matches the conviction level and market conditions
- Take-profit: is it realistic given current price action and volatility?
- Stop-loss: does it protect against real risk without triggering on normal fluctuations?

Challenge both the aggressive and conservative analysts. Point out where the aggressive stance takes unnecessary gambles AND where the conservative stance leaves money on the table.

{data_context}
Conversation history: {history}
Last aggressive argument: {current_aggressive_response}
Last conservative argument: {current_conservative_response}

If there are no responses from the other viewpoints yet, present your own argument based on the available data. Speak conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
