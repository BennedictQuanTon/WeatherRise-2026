"""
Tourism Context Agent — V3
Full pipeline: KB check → Gap Report → MCP → Entity Linking → Trip Plan Assembly.
Handles both simple weather queries and multi-day trip planning.
"""
from typing import List
from agents.context_agents.base_context_agent import BaseContextAgent
from agents.context_agents.tourism_agent.trip_context_planner import build_trip_plan
from apps.api.app.schemas.context_schema import (
    ParserOutput, MCPContext, FullyProcessedPayload,
    KnowledgeContext, IntelligenceRequirements, ContextStatus
)

OUTDOOR_INTENTS = {"travel_planning", "sightseeing", "beach", "hiking", "outdoor_activity"}
BEACH_INTENTS = {"beach", "swimming", "surfing"}


class TourismContextAgent(BaseContextAgent):
    domain = "tourism"

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = ["weather_forecast", "tourist_attractions", "weather_risk_rules"]
        if parsed.intent_subtype == "multi_day_trip_planning":
            ctx += [
                "restaurants", "distance_matrix", "opening_hours",
                "indoor_outdoor_classification", "trip_route_plan", "backup_plan_options",
            ]
        elif any(k in intent for k in OUTDOOR_INTENTS):
            ctx += ["opening_hours", "backup_plan_options"]
        if any(k in intent for k in BEACH_INTENTS):
            ctx += ["storm_risk", "uv_index"]
        return list(dict.fromkeys(ctx))

    def get_weather_variables(self, intent: str) -> List[str]:
        base = ["rain_probability", "temperature", "wind_speed", "humidity"]
        if "beach" in intent.lower():
            base += ["uv_index", "storm_risk"]
        return base

    async def enrich_mcp_context(self, parsed: ParserOutput, mcp_ctx: MCPContext) -> MCPContext:
        """Fetch attractions + restaurants, build trip plan for multi-day queries."""
        location = parsed.location or "Da Nang"

        # 1. Search tourist attractions (OSM/local)
        places_result = await self.call_mcp("place.searchPlaces", {
            "location": location,
            "category": "tourist_attraction",
            "limit": 20,
        })
        attractions = places_result.get("results", [])
        mcp_ctx.places = attractions

        # 2. For trip planning: also fetch restaurants
        if parsed.intent_subtype == "multi_day_trip_planning":
            rest_result = await self.call_mcp("place.searchRestaurants", {
                "location": location,
                "limit": 20,
            })
            restaurants = rest_result.get("results", [])
            mcp_ctx.restaurants = restaurants

            # 3. Build trip plan
            duration_days = (parsed.trip_request.duration_days or 3) if parsed.trip_request else 3
            trip_plan = build_trip_plan(
                attractions=attractions,
                restaurants=restaurants,
                duration_days=duration_days,
                location=location,
            )
            mcp_ctx.trip_plan_context = trip_plan

        return mcp_ctx

    async def process(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """V3 pipeline: coordinates → time → weather → enrich → assemble."""
        involved_context = self.get_required_context(parsed)
        mcp_ctx = MCPContext()

        # 1. Resolve coordinates
        if parsed.location:
            coord_result = await self.call_mcp("location.resolveCoordinates", {
                "location": parsed.location
            })
            if coord_result.get("latitude"):
                mcp_ctx.coordinates = {
                    "latitude": coord_result["latitude"],
                    "longitude": coord_result["longitude"],
                }
                parsed.geographical_location.coordinates = mcp_ctx.coordinates

        # Fallback to Da Nang coords
        if not mcp_ctx.coordinates:
            mcp_ctx.coordinates = {"latitude": 16.0544, "longitude": 108.2022}
            parsed.geographical_location.coordinates = mcp_ctx.coordinates

        # 2. Resolve time range
        if parsed.time_range.raw_text:
            time_result = await self.call_mcp("time.resolveTimeRange", {
                "raw_text": parsed.time_range.raw_text,
                "timezone": parsed.time_range.timezone,
            })
            if time_result.get("start"):
                parsed.time_range.start = time_result["start"]
                parsed.time_range.end = time_result.get("end")
                mcp_ctx.time_range_resolved = time_result

        # Fallback dates
        if not parsed.time_range.start or not parsed.time_range.end:
            from datetime import datetime, timedelta
            now = datetime.now()
            parsed.time_range.start = parsed.time_range.start or now.strftime("%Y-%m-%d")
            parsed.time_range.end = parsed.time_range.end or (
                now + timedelta(days=(parsed.trip_request.duration_days or 3) if parsed.trip_request else 3)
            ).strftime("%Y-%m-%d")

        # 3. Get weather forecast
        forecast = await self.call_mcp("weather.getForecast", {
            "latitude": mcp_ctx.coordinates["latitude"],
            "longitude": mcp_ctx.coordinates["longitude"],
            "start_date": parsed.time_range.start,
            "end_date": parsed.time_range.end,
        })
        if forecast:
            mcp_ctx.weather_forecast = forecast

        # 4. Domain-specific enrichment (places, restaurants, trip plan)
        mcp_ctx = await self.enrich_mcp_context(parsed, mcp_ctx)

        # 5. Determine context quality
        is_trip = parsed.intent_subtype == "multi_day_trip_planning"
        has_trip_plan = bool(mcp_ctx.trip_plan_context and mcp_ctx.trip_plan_context.get("days"))
        has_places = bool(mcp_ctx.places)

        if is_trip and has_trip_plan:
            quality = "usable_for_trip_planning"
        elif has_places:
            quality = "usable_for_prediction"
        else:
            quality = "partial"

        context_status = ContextStatus(
            knowledge_base_complete=False,
            mcp_called=True,
            missing_context_resolved=True,
            context_quality=quality,
            trip_plan_ready=has_trip_plan,
            weather_optimization_ready=bool(mcp_ctx.weather_forecast),
        )

        return FullyProcessedPayload(
            domain=self.domain,
            intent=parsed.intent,
            intent_subtype=parsed.intent_subtype,
            location=parsed.location,
            geographical_location=parsed.geographical_location,
            time_range=parsed.time_range,
            trip_request=parsed.trip_request,
            involved_context=involved_context,
            knowledge_context=KnowledgeContext(),
            mcp_context=mcp_ctx,
            context_status=context_status,
            intelligence_requirements=IntelligenceRequirements(
                realtime_weather_needed=True,
                weather_variables=self.get_weather_variables(parsed.intent),
                reasoning_task=(
                    "tourism_multi_day_trip_planning"
                    if is_trip else f"tourism_{parsed.intent}"
                ),
            ),
            user_constraints=parsed.user_constraints,
            raw_user_input=parsed.raw_user_input,
        )
