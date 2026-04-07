import json


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        conservative_history = risk_debate_state.get("conservative_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

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
            data_context = f"""Draw from the following data sources to build a convincing case for a low-risk approach:

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}"""
        else:
            data_context = "Draw from the debate history to build a convincing case for a low-risk approach."

        prompt = f"""As the Conservative Risk Analyst, your primary objective is to protect capital and minimize downside risk. You are reviewing the Trader's specific plan and debating whether the parameters expose the firm to excessive risk.

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'N/A')}
- Target position: {trader_plan.get('target_position_pct', 'N/A')}% of capital
- Take-profit: {trader_plan.get('take_profit_price', 'N/A')}
- Stop-loss: {trader_plan.get('stop_loss_price', 'N/A')}

**Your stance — argue for safer parameters:**
- Position size should be SMALLER (e.g. if Trader says 40%, argue for 20% or less)
- Take-profit should be LOWER (secure gains earlier, don't get greedy)
- Stop-loss should be TIGHTER (limit maximum loss per trade)

Respond directly to the aggressive and neutral analysts' specific arguments. Point out where their optimism ignores concrete risks.

{data_context}
Conversation history: {history}
Last aggressive argument: {current_aggressive_response}
Last neutral argument: {current_neutral_response}

If there are no responses from the other viewpoints yet, present your own argument based on the available data. Speak conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Conservative Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": argument,
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
