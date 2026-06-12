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
    _http_client: httpx.AsyncClient | None = None

    @classmethod
    def get_http_client(cls) -> httpx.AsyncClient:
        if cls._http_client is None or cls._http_client.is_closed:
            cls._http_client = httpx.AsyncClient(
                timeout=15.0,
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=20,
                ),
            )
        return cls._http_client

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        """Override in subclasses to return domain-specific context list."""
        raise NotImplementedError

    def get_weather_variables(self, intent: str) -> List[str]:
        """Override in subclasses to return required weather variables."""
        return ["rain_probability", "temperature", "wind_speed", "humidity"]

    async def call_mcp(self, route: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call a MCP route and return the result.

        Converts dot-notation (e.g. 'location.resolveCoordinates') to
        REST path notation ('/tools/location/resolveCoordinates') to match
        MCP server router mount points.
        """
        try:
            # Phase 1 Bug Fix: dot → slash for REST path
            url_path = route.replace(".", "/")
            client = self.get_http_client()
            r = await client.post(
                f"{MCP_SERVER_URL}/tools/{url_path}",
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

        # 1. Resolve coordinates and time range concurrently via MCP
        coord_task = None
        time_task = None
        
        if parsed.geographical_location.coordinates and parsed.geographical_location.coordinates.get("latitude"):
            mcp_ctx.coordinates = parsed.geographical_location.coordinates
        elif parsed.location:
            import asyncio
            coord_task = asyncio.create_task(
                self.call_mcp("location.resolveCoordinates", {"location": parsed.location})
            )

        if parsed.time_range.raw_text:
            import asyncio
            time_task = asyncio.create_task(
                self.call_mcp("time.resolveTimeRange", {
                    "raw_text": parsed.time_range.raw_text,
                    "timezone": parsed.time_range.timezone,
                })
            )

        if coord_task:
            coord_result = await coord_task
            if coord_result.get("latitude"):
                mcp_ctx.coordinates = {
                    "latitude": coord_result["latitude"],
                    "longitude": coord_result["longitude"],
                }
                parsed.geographical_location.coordinates = mcp_ctx.coordinates

        if time_task:
            time_result = await time_task
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
