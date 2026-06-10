"""
Base Context Agent — shared logic for all domain context agents.
"""
import httpx
import os
from typing import List, Dict, Any
from apps.api.app.schemas.context_schema import (
    ParserOutput, FullyProcessedPayload,
    KnowledgeContext, MCPContext, IntelligenceRequirements,
)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:9000")


class BaseContextAgent:
    domain: str = "base"

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        """Override in subclasses to return domain-specific context list."""
        raise NotImplementedError

    def get_weather_variables(self, intent: str) -> List[str]:
        """Override in subclasses to return required weather variables."""
        return ["rain_probability", "temperature", "wind_speed", "humidity"]

    async def call_mcp(self, route: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call a MCP route and return the result."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{MCP_SERVER_URL}/tools/{route}",
                    json=payload,
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            print(f"[MCP] Error calling {route}: {e}")
            return {}

    async def process(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """Full context agent pipeline: fill context → query KB → call MCP for missing."""
        involved_context = self.get_required_context(parsed)
        mcp_ctx = MCPContext()

        # 1. Resolve coordinates via MCP
        if parsed.location:
            coord_result = await self.call_mcp("location.resolveCoordinates", {
                "location": parsed.location
            })
            if coord_result.get("latitude"):
                mcp_ctx.coordinates = {
                    "latitude": coord_result["latitude"],
                    "longitude": coord_result["longitude"],
                }
                # Fill back into geographical_location
                parsed.geographical_location.coordinates = mcp_ctx.coordinates

        # 2. Resolve time range via MCP
        if parsed.time_range.raw_text:
            time_result = await self.call_mcp("time.resolveTimeRange", {
                "raw_text": parsed.time_range.raw_text,
                "timezone": parsed.time_range.timezone,
            })
            if time_result.get("start"):
                parsed.time_range.start = time_result["start"]
                parsed.time_range.end = time_result.get("end")
                mcp_ctx.time_range_resolved = time_result

        # Fallback to default start/end dates if not resolved
        if not parsed.time_range.start or not parsed.time_range.end:
            from datetime import datetime, timedelta
            now = datetime.now()
            parsed.time_range.start = parsed.time_range.start or now.strftime("%Y-%m-%d")
            parsed.time_range.end = parsed.time_range.end or (now + timedelta(days=3)).strftime("%Y-%m-%d")

        # 3. Get weather forecast via MCP
        if mcp_ctx.coordinates:
            forecast = await self.call_mcp("weather.getForecast", {
                "latitude": mcp_ctx.coordinates["latitude"],
                "longitude": mcp_ctx.coordinates["longitude"],
                "start_date": parsed.time_range.start,
                "end_date": parsed.time_range.end,
            })
            if forecast:
                mcp_ctx.weather_forecast = forecast

        # 4. Domain-specific MCP calls (override in subclasses)
        mcp_ctx = await self.enrich_mcp_context(parsed, mcp_ctx)

        return FullyProcessedPayload(
            domain=self.domain,
            intent=parsed.intent,
            location=parsed.location,
            geographical_location=parsed.geographical_location,
            time_range=parsed.time_range,
            involved_context=involved_context,
            knowledge_context=KnowledgeContext(),
            mcp_context=mcp_ctx,
            intelligence_requirements=IntelligenceRequirements(
                realtime_weather_needed=True,
                weather_variables=self.get_weather_variables(parsed.intent),
                reasoning_task=f"{self.domain}_{parsed.intent}",
            ),
            user_constraints=parsed.user_constraints,
            raw_user_input=parsed.raw_user_input,
        )

    async def enrich_mcp_context(
        self, parsed: ParserOutput, mcp_ctx: MCPContext
    ) -> MCPContext:
        """Override in subclasses for domain-specific MCP enrichment."""
        return mcp_ctx
