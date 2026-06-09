"""
Construction Context Agent
Knows concrete pouring requires rain, humidity, temp, wind.
Crane operation requires wind speed and gust risk.
"""
from typing import List
from agents.context_agents.base_context_agent import BaseContextAgent
from apps.api.app.schemas.context_schema import ParserOutput, MCPContext

CONCRETE_INTENTS = {"concrete_pouring", "concrete", "foundation"}
CRANE_INTENTS = {"crane", "lifting", "crane_operation"}


class ConstructionContextAgent(BaseContextAgent):
    domain = "construction"

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = ["weather_forecast", "construction_safety_thresholds", "weather_risk_rules"]
        if any(k in intent for k in CONCRETE_INTENTS):
            ctx += ["humidity_levels", "temperature_range", "rain_probability"]
        if any(k in intent for k in CRANE_INTENTS):
            ctx += ["wind_speed", "gust_risk"]
        ctx += ["outdoor_worker_safety"]
        return list(dict.fromkeys(ctx))

    def get_weather_variables(self, intent: str) -> List[str]:
        base = ["rain_probability", "temperature", "wind_speed", "humidity"]
        if "crane" in intent.lower():
            base += ["wind_gusts", "storm_warning"]
        return base

    async def enrich_mcp_context(self, parsed: ParserOutput, mcp_ctx: MCPContext) -> MCPContext:
        """Get external risk data for construction domain."""
        if parsed.location:
            risk_data = await self.call_mcp("domain.getExternalRiskData", {
                "domain": "construction",
                "location": parsed.location,
                "intent": parsed.intent,
            })
            if risk_data:
                mcp_ctx.external_risk_data = risk_data
        return mcp_ctx
