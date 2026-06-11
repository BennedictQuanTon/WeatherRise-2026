"""
Context Assembler — V3
Final step: merges parser output + KB context + MCP context → FullyProcessedPayload.
Applies entity linking, forecast enrichment, context quality assessment.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from agents.context_agents.context_gap_report import ContextGapReport
from agents.context_agents.entity_linker import EntityLinker
from apps.api.app.schemas.context_schema import (
    FullyProcessedPayload, ParserOutput, MCPContext,
    KnowledgeContext, IntelligenceRequirements, ContextStatus,
)


_linker = EntityLinker()


def _extract_daily_forecasts(mcp_ctx: MCPContext) -> List[Dict]:
    """Pull daily_forecasts from weather_forecast envelope output."""
    wf = mcp_ctx.weather_forecast or {}
    # Handle both envelope format and raw format
    if "output" in wf:
        return wf["output"].get("daily_forecasts", [])
    return wf.get("daily_forecasts", [])


def _extract_attractions(mcp_ctx: MCPContext) -> List[Dict]:
    """Get attractions from MCP context (handles envelope or raw list)."""
    places = mcp_ctx.places or []
    if isinstance(places, dict):
        # Envelope format from search_places
        return places.get("output", {}).get("attractions", [])
    return places


def _extract_restaurants(mcp_ctx: MCPContext) -> List[Dict]:
    """Get restaurants from MCP context."""
    rests = mcp_ctx.restaurants or []
    if isinstance(rests, dict):
        return rests.get("output", {}).get("restaurants", [])
    return rests


def _determine_quality(
    is_trip: bool,
    has_trip_plan: bool,
    has_places: bool,
    has_forecast: bool,
    missing_critical: List[str],
) -> str:
    """Determine context_quality string for intelligence layer routing."""
    if missing_critical:
        return "partial"
    if is_trip and has_trip_plan and has_forecast:
        return "usable_for_trip_planning"
    if has_places and has_forecast:
        return "usable_for_prediction"
    if has_places or has_forecast:
        return "partial"
    return "blocked"


def assemble_context(
    parsed: ParserOutput,
    mcp_ctx: MCPContext,
    gap_report: ContextGapReport,
    kb_context: Optional[KnowledgeContext] = None,
    mcp_routes_called: Optional[List[str]] = None,
) -> FullyProcessedPayload:
    """
    Core assembly function: merge all context sources → FullyProcessedPayload.
    Applies entity linking and per-stop forecast enrichment.
    """
    domain = gap_report.domain
    is_trip = parsed.intent_subtype == "multi_day_trip_planning"
    mcp_routes_called = mcp_routes_called or []

    # Extract structured data
    attractions = _extract_attractions(mcp_ctx)
    restaurants = _extract_restaurants(mcp_ctx)
    daily_forecasts = _extract_daily_forecasts(mcp_ctx)

    # Build entity registry from available places
    registry = _linker.build_registry(attractions, restaurants)

    # Enrich trip plan with entity links + forecast
    trip_plan = mcp_ctx.trip_plan_context or {}
    all_warnings = list(gap_report.missing_types)

    if trip_plan and trip_plan.get("days"):
        enriched_days = []
        for day_idx, day in enumerate(trip_plan["days"]):
            # Entity link validation + metadata merge
            link_result = _linker.validate_trip_plan(
                {"days": [day]}, registry
            )
            if link_result.warnings:
                all_warnings.extend(link_result.warnings)

            # Weather forecast enrichment per stop
            enriched_stops = _linker.enrich_stops_with_forecast(
                stops=link_result.enriched_stops,
                daily_forecasts=daily_forecasts,
                day_idx=day_idx,
            )

            # Weather-aware reordering: put indoor stops first on rainy days
            day_date = None
            day_weather = None
            day_temp_range = None
            day_rain_prob = None

            if daily_forecasts and day_idx < len(daily_forecasts):
                df = daily_forecasts[day_idx]
                day_date = df.get("date")
                max_rain = df.get("max_rain_prob_pct", 0)
                day_rain_prob = max_rain
                
                if max_rain >= 60:
                    day_weather = "Rainy"
                elif max_rain >= 35:
                    day_weather = "Rain Chance"
                else:
                    day_weather = "Dry"
                
                min_t = df.get("min_temp_c")
                max_t = df.get("max_temp_c")
                if min_t is not None and max_t is not None:
                    day_temp_range = f"{min_t}-{max_t}°C"
                else:
                    day_temp_range = df.get("dominant_weather")
                
                if df.get("max_rain_prob_pct", 0) >= 60:
                    enriched_stops = sorted(
                        enriched_stops,
                        key=lambda s: (0 if s.get("is_indoor") else 1, s.get("order", 99))
                    )
                    # Re-number after sort
                    for i, s in enumerate(enriched_stops):
                        s["order"] = i + 1
            else:
                from datetime import datetime, timedelta
                try:
                    start_dt = datetime.strptime(parsed.time_range.start, "%Y-%m-%d")
                    day_date = (start_dt + timedelta(days=day_idx)).strftime("%Y-%m-%d")
                except Exception:
                    pass

            enriched_days.append({
                **day,
                "stops": enriched_stops,
                "date": day_date,
                "weather_condition": day_weather,
                "temp_range": day_temp_range,
                "rain_prob": day_rain_prob,
            })

        trip_plan = {**trip_plan, "days": enriched_days, "weather_aware": True}
        mcp_ctx.trip_plan_context = trip_plan

    # Determine quality
    has_trip_plan = bool(trip_plan.get("days"))
    has_places = bool(attractions)
    has_forecast = bool(daily_forecasts)

    quality = _determine_quality(
        is_trip=is_trip,
        has_trip_plan=has_trip_plan,
        has_places=has_places,
        has_forecast=has_forecast,
        missing_critical=gap_report.critical_missing,
    )

    # Fallback time range if missing
    if not parsed.time_range.start:
        now = datetime.now()
        parsed.time_range.start = now.strftime("%Y-%m-%d")
        parsed.time_range.end = (
            now + timedelta(days=(parsed.trip_request.duration_days or 3) if parsed.trip_request else 3)
        ).strftime("%Y-%m-%d")

    context_status = ContextStatus(
        knowledge_base_complete=gap_report.is_complete,
        mcp_called=bool(mcp_routes_called),
        missing_context_resolved=len(gap_report.critical_missing) == 0,
        context_quality=quality,
        trip_plan_ready=has_trip_plan,
        weather_optimization_ready=has_forecast,
    )

    return FullyProcessedPayload(
        domain=domain,
        intent=parsed.intent,
        intent_subtype=parsed.intent_subtype,
        location=parsed.location,
        geographical_location=parsed.geographical_location,
        time_range=parsed.time_range,
        trip_request=parsed.trip_request,
        involved_context=gap_report.required_context,
        knowledge_context=kb_context or KnowledgeContext(),
        mcp_context=mcp_ctx,
        context_status=context_status,
        intelligence_requirements=IntelligenceRequirements(
            realtime_weather_needed=True,
            weather_variables=["rain_probability", "temperature", "wind_speed", "humidity"],
            reasoning_task=(
                "tourism_multi_day_trip_planning"
                if is_trip else f"tourism_{parsed.intent}"
            ),
        ),
        user_constraints=parsed.user_constraints,
        raw_user_input=parsed.raw_user_input,
    )
