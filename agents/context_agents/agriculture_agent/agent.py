"""
Agriculture Context Agent
Knows irrigation requires rainfall forecast, soil moisture, crop type, temperature.
Disease risk requires humidity, recent rainfall, crop profile, temperature range.
"""
from typing import List
from agents.context_agents.base_context_agent import BaseContextAgent
from apps.api.app.schemas.context_schema import ParserOutput, MCPContext

IRRIGATION_INTENTS = {"irrigation", "watering", "irrigate"}
HARVEST_INTENTS = {"harvest", "harvesting"}
DISEASE_INTENTS = {"disease", "pest", "blight", "fungal"}


class AgricultureContextAgent(BaseContextAgent):
    domain = "agriculture"

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = ["weather_forecast", "agriculture_safety_thresholds", "weather_risk_rules"]
        if any(k in intent for k in IRRIGATION_INTENTS):
            ctx += ["rainfall_forecast", "soil_moisture", "temperature_range", "crop_type"]
        if any(k in intent for k in HARVEST_INTENTS):
            ctx += ["rainfall", "field_accessibility", "crop_maturity_window"]
        if any(k in intent for k in DISEASE_INTENTS):
            ctx += ["humidity_levels", "recent_rainfall", "crop_profile", "temperature_range"]
        return list(dict.fromkeys(ctx))

    def get_weather_variables(self, intent: str) -> List[str]:
        base = ["rain_probability", "temperature", "humidity", "wind_speed"]
        if "irrigation" in intent.lower():
            base += ["soil_moisture_proxy", "evapotranspiration"]
        if "disease" in intent.lower():
            base += ["dew_point", "leaf_wetness_hours"]
        return base

    async def enrich_mcp_context(self, parsed: ParserOutput, mcp_ctx: MCPContext) -> MCPContext:
        """Get external agricultural risk data."""
        if parsed.location:
            risk_data = await self.call_mcp("domain.getExternalRiskData", {
                "domain": "agriculture",
                "location": parsed.location,
                "intent": parsed.intent,
            })
            if risk_data:
                mcp_ctx.external_risk_data = risk_data
        return mcp_ctx
