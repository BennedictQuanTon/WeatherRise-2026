"""
Tourism Context Agent — V3 Full Pipeline
Flow:
  1. Resolve coordinates (known_coords fast-path or Nominatim)
  2. Resolve time range
  3. Get weather forecast (Open-Meteo via MCP)
  4. KB query (TourismRetriever 3-tier: Qdrant → Overpass → mock)
  5. Build ContextGapReport
  6. Call MCP for missing context only
  7. Build trip plan (attractions + interleaved restaurants)
  8. EntityLinker: validate + enrich stops with forecast
  9. Assemble FullyProcessedPayload
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any

from agents.context_agents.base_context_agent import BaseContextAgent
from agents.context_agents.context_gap_report import build_context_gap_report
from agents.context_agents.entity_linker import EntityLinker
from agents.context_agents.context_assembler import assemble_context
from agents.context_agents.tourism_agent.trip_context_planner import build_trip_plan
from knowledge.retrievers.tourism_retriever import TourismRetriever
from apps.api.app.schemas.context_schema import (
    ParserOutput, MCPContext, FullyProcessedPayload,
    KnowledgeContext, IntelligenceRequirements, ContextStatus,
)

OUTDOOR_INTENTS = {"travel_planning", "sightseeing", "beach", "hiking", "outdoor_activity"}
BEACH_INTENTS = {"beach", "swimming", "surfing"}


class TourismContextAgent(BaseContextAgent):
    domain = "tourism"

    def __init__(self):
        super().__init__()
        self._retriever = TourismRetriever()
        self._linker = EntityLinker()

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = ["weather_forecast", "tourist_attractions", "weather_risk_rules"]
        if parsed.intent_subtype == "multi_day_trip_planning":
            ctx += [
                "restaurants", "opening_hours",
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

    async def process(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """Full V3 pipeline with KB-Miss → Live Fetch → Context Assembly."""
        location = parsed.location or "Da Nang"
        mcp_ctx = MCPContext()
        mcp_routes_called = []

        # ── 1. Resolve Coordinates ───────────────────────────────
        coord_result = await self.call_mcp("location.resolveCoordinates", {"location": location})
        mcp_routes_called.append("location.resolveCoordinates")

        coords = coord_result.get("output", coord_result)  # handle both envelope and raw
        lat = coords.get("latitude") or 16.0544
        lon = coords.get("longitude") or 108.2022
        mcp_ctx.coordinates = {"latitude": lat, "longitude": lon}
        parsed.geographical_location.coordinates = mcp_ctx.coordinates

        # ── 2. Resolve Time Range ────────────────────────────────
        if parsed.time_range and parsed.time_range.raw_text:
            time_result = await self.call_mcp("time.resolveTimeRange", {
                "raw_text": parsed.time_range.raw_text,
                "timezone": getattr(parsed.time_range, "timezone", "Asia/Ho_Chi_Minh"),
            })
            mcp_routes_called.append("time.resolveTimeRange")
            tr = time_result.get("output", time_result)
            if tr.get("start"):
                parsed.time_range.start = tr["start"]
                parsed.time_range.end = tr.get("end")
                mcp_ctx.time_range_resolved = tr

        # Fallback dates
        if not (parsed.time_range and parsed.time_range.start):
            now = datetime.now()
            n_days = (
                (parsed.trip_request.duration_days or 3)
                if parsed.trip_request else 3
            )
            if parsed.time_range:
                parsed.time_range.start = now.strftime("%Y-%m-%d")
                parsed.time_range.end = (now + timedelta(days=n_days)).strftime("%Y-%m-%d")

        # Ensure end date covers duration if it's a trip
        if parsed.time_range and parsed.time_range.start and parsed.trip_request and parsed.trip_request.duration_days:
            try:
                start_dt = datetime.strptime(parsed.time_range.start, "%Y-%m-%d")
                duration = parsed.trip_request.duration_days
                current_end = parsed.time_range.end
                if current_end:
                    end_dt = datetime.strptime(current_end, "%Y-%m-%d")
                    if (end_dt - start_dt).days < duration:
                        parsed.time_range.end = (start_dt + timedelta(days=duration)).strftime("%Y-%m-%d")
                else:
                    parsed.time_range.end = (start_dt + timedelta(days=duration)).strftime("%Y-%m-%d")
            except Exception:
                pass

        # ── 3. Weather Forecast ──────────────────────────────────
        forecast_result = await self.call_mcp("weather.getForecast", {
            "latitude": lat,
            "longitude": lon,
            "start_date": getattr(parsed.time_range, "start", None),
            "end_date": getattr(parsed.time_range, "end", None),
        })
        mcp_routes_called.append("weather.getForecast")
        if forecast_result:
            mcp_ctx.weather_forecast = forecast_result

        # ── 4. KB Query: TourismRetriever 3-tier ─────────────────
        kb_attractions = await self._retriever.get_attractions(
            location=location,
            coordinates=mcp_ctx.coordinates,
            limit=20,
        )
        kb_restaurants = await self._retriever.get_restaurants(
            location=location,
            coordinates=mcp_ctx.coordinates,
            limit=15,
        )

        # ── 5. Context Gap Report ────────────────────────────────
        involved_context = self.get_required_context(parsed)
        kb_data = {
            "tourist_attractions": kb_attractions.data if not kb_attractions.is_empty else None,
            "weather_forecast": bool(mcp_ctx.weather_forecast),
            "restaurants": kb_restaurants.data if not kb_restaurants.is_empty else None,
        }
        gap_report = build_context_gap_report(
            required=involved_context,
            kb_results=kb_data,
            domain=self.domain,
            location=location,
        )

        # ── 6. Fill MCP context with KB results ──────────────────
        mcp_ctx.places = kb_attractions.data
        mcp_ctx.restaurants = kb_restaurants.data

        # ── 7. Build Trip Plan (if multi-day) ────────────────────
        is_trip = parsed.intent_subtype == "multi_day_trip_planning"
        if is_trip and kb_attractions.data:
            duration_days = (
                (parsed.trip_request.duration_days or 3)
                if parsed.trip_request else 3
            )
            daily_forecasts = (
                forecast_result.get("output", {}).get("daily_forecasts", [])
                if isinstance(forecast_result, dict) else []
            )
            trip_plan = build_trip_plan(
                attractions=kb_attractions.data,
                restaurants=kb_restaurants.data,
                duration_days=duration_days,
                location=location,
                weather_forecasts=None,  # Handled by ContextAssembler
            )
            mcp_ctx.trip_plan_context = trip_plan

        # ── 8. Assemble + Entity Link + Forecast Enrich ──────────
        return assemble_context(
            parsed=parsed,
            mcp_ctx=mcp_ctx,
            gap_report=gap_report,
            kb_context=KnowledgeContext(),
            mcp_routes_called=mcp_routes_called,
        )
