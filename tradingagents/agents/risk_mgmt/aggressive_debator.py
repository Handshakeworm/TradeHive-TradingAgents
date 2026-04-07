import json


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
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
            data_context = f"""Incorporate insights from the following sources into your arguments:

Market Research Report: {market_research_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}"""
        else:
            data_context = ""

        prompt = f"""As the Aggressive Risk Analyst, your role is to argue for MAXIMIZING returns by taking on more risk. You are reviewing the Trader's specific plan and debating whether the parameters are too conservative.

**Trader's Proposed Plan:**
- Action: {trader_plan.get('action', 'N/A')}
- Target position: {trader_plan.get('target_position_pct', 'N/A')}% of capital
- Take-profit: {trader_plan.get('take_profit_price', 'N/A')}
- Stop-loss: {trader_plan.get('stop_loss_price', 'N/A')}

**Your stance — argue for bolder parameters:**
- Position size should be LARGER (e.g. if Trader says 30%, argue for 50%+)
- Take-profit should be HIGHER (don't cap upside too early)
- Stop-loss should be WIDER (give the trade room to breathe, avoid being stopped out by noise)

Respond directly to the conservative and neutral analysts' specific counter-arguments. Use data to support why higher risk is justified here.

{data_context}
Conversation history: {history}
Last conservative argument: {current_conservative_response}
Last neutral argument: {current_neutral_response}

If there are no responses from the other viewpoints yet, present your own argument based on the available data. Speak conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
