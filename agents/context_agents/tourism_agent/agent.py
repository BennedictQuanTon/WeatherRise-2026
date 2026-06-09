"""
Tourism Context Agent
Fills context for tourism/travel planning queries.
Knows that outdoor activities need rain, wind, UV, storm risk, and backup indoor plans.
"""
from typing import List
from agents.context_agents.base_context_agent import BaseContextAgent
from apps.api.app.schemas.context_schema import ParserOutput, MCPContext

OUTDOOR_INTENTS = {"travel_planning", "sightseeing", "beach", "hiking", "outdoor_activity"}
BEACH_INTENTS = {"beach", "swimming", "surfing"}


class TourismContextAgent(BaseContextAgent):
    domain = "tourism"

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = [
            "weather_forecast",
            "tourist_attractions",
            "indoor_outdoor_classification",
            "weather_risk_rules",
        ]
        if any(k in intent for k in OUTDOOR_INTENTS):
            ctx += ["opening_hours", "travel_time", "backup_plan_options"]
        if any(k in intent for k in BEACH_INTENTS):
            ctx += ["storm_risk", "uv_index"]
        return list(dict.fromkeys(ctx))  # deduplicate while preserving order

    def get_weather_variables(self, intent: str) -> List[str]:
        base = ["rain_probability", "temperature", "wind_speed", "humidity"]
        if "beach" in intent.lower():
            base += ["uv_index", "storm_risk", "wave_height"]
        return base

    async def enrich_mcp_context(self, parsed: ParserOutput, mcp_ctx: MCPContext) -> MCPContext:
        """Search for places and get opening hours."""
        if parsed.location:
            places = await self.call_mcp("place.searchPlaces", {
                "location": parsed.location,
                "category": "tourist_attraction",
            })
            if places:
                mcp_ctx.places = places.get("results", [])
        return mcp_ctx
