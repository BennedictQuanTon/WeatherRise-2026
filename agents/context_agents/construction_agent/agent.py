"""
Construction Context Agent — V3 (Controlled Fragmentation / Fallback Forced)
Knows concrete pouring requires rain, humidity, temp, wind.
Crane operation requires wind speed and gust risk.
Loads incomplete local KB tracking parameters to explicitly force live MCP calls.
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import List

from apps.api.app.routes.monitor import emit
from agents.context_agents.base_context_agent import BaseContextAgent
from apps.api.app.schemas.context_schema import (
    ParserOutput, MCPContext, FullyProcessedPayload,
    KnowledgeContext, IntelligenceRequirements, ContextStatus
)

CONCRETE_INTENTS = {"concrete_pouring", "concrete", "foundation"}
CRANE_INTENTS = {"crane", "lifting", "crane_operation"}
SEED_DATA_PATH = "knowledge/seed_data/construction/danang_sites.json"


def _normalize_id(value: str) -> str:
    """Canonical normalization: lowercase, strip, collapse spaces to underscores.

    Handles edge cases the parser may emit:
        'Da Nang BRT Corridor Phase 2'  ->  'da_nang_brt_corridor_phase_2'
        'danang_brt_corridor_phase2'    ->  'danang_brt_corridor_phase2'  (unchanged)
        '  Hoa Lien  '                 ->  'hoa_lien'
    """
    return value.strip().lower().replace(" ", "_")


def _resolve_site_record(catalog: list, raw_location: str) -> dict:
    """Three-tier KB lookup with progressive fallback.

    Tier 1 - Exact site_id match (normalized both sides).
    Tier 2 - Normalized site_name match (handles LLM-resolved display names).
    Tier 3 - project_type or city substring match (partial query like 'bridge' or 'lien chieu').

    Returns the matched record dict, or {} if nothing matches.
    """
    norm_query = _normalize_id(raw_location)

    # Tier 1: exact site_id match
    for item in catalog:
        if _normalize_id(item.get("site_id", "")) == norm_query:
            print(f"[KB] Tier-1 match on site_id: {item['site_id']}")
            return item

    # Tier 2: normalized site_name match
    for item in catalog:
        if _normalize_id(item.get("site_name", "")) == norm_query:
            print(f"[KB] Tier-2 match on site_name: {item['site_name']}")
            return item

    # Tier 3: substring match against project_type or city
    for item in catalog:
        project_type = _normalize_id(item.get("project_type", ""))
        city = _normalize_id(item.get("city", ""))
        if norm_query in project_type or norm_query in city:
            print(f"[KB] Tier-3 partial match on project_type/city for query='{raw_location}'")
            return item

    print(f"[KB] No match found for query='{raw_location}' (normalized='{norm_query}')")
    return {}


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
        base = ["rain_probability", "temperature_c", "wind_speed_kmh", "humidity_percent"]
        if "crane" in intent.lower():
            base += ["wind_gust_kmh", "storm_warning"]
        return base

    async def process(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """Overridden pipeline to demonstrate KB cache-miss -> live MCP recovery trace."""
        involved_context = self.get_required_context(parsed)
        mcp_ctx = MCPContext()
        knowledge_context = KnowledgeContext()

        # 1. Enforce default coordinates fallback
        t_phase1 = time.time()
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

        if not mcp_ctx.coordinates:
            mcp_ctx.coordinates = {"latitude": 16.0471, "longitude": 108.2062}  # Da Nang Industrial Zone Centroid
            parsed.geographical_location.coordinates = mcp_ctx.coordinates

        # 2. Synchronize temporal targets
        if parsed.time_range.raw_text:
            time_result = await self.call_mcp("time.resolveTimeRange", {
                "raw_text": parsed.time_range.raw_text,
                "timezone": parsed.time_range.timezone,
            })
            if time_result.get("start"):
                parsed.time_range.start = time_result["start"]
                parsed.time_range.end = time_result.get("end")
                mcp_ctx.time_range_resolved = time_result

        if not parsed.time_range.start or not parsed.time_range.end:
            now = datetime.now()
            parsed.time_range.start = parsed.time_range.start or now.strftime("%Y-%m-%d")
            parsed.time_range.end = parsed.time_range.end or (now + timedelta(days=1)).strftime("%Y-%m-%d")

        ms_phase1 = int((time.time() - t_phase1) * 1000)
        emit("step", "ConstructionAgent", "Phase I: Coordinates & Time resolved", duration_ms=ms_phase1)

        # 3. Interrogate Fragmented Knowledge Base (Forced Cache-Miss)
        t_phase2 = time.time()
        target_site = parsed.location or "DN_SITE_ZONE_3"
        kb_record = {}

        if os.path.exists(SEED_DATA_PATH):
            try:
                with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                catalog = data if isinstance(data, list) else list(data.values())
                kb_record = _resolve_site_record(catalog, target_site)
            except Exception as e:
                print(f"[KB Error] Failed to read construction seed data: {e}")

        # Distribute parameters to show partial matching
        if kb_record:
            for k, v in kb_record.items():
                if v is not None:
                    knowledge_context.found_context[k] = v
                else:
                    knowledge_context.missing_context.append(k)
        else:
            knowledge_context.missing_context = ["thresholds", "safety_margins"]
            print(f"[KB Miss] No record matched for location='{target_site}'. MCP recovery required.")

        ms_phase2 = int((time.time() - t_phase2) * 1000)
        emit("step", "ConstructionAgent", "Phase II: KB Cache Search", duration_ms=ms_phase2)

        # 4. Trigger Live MCP Recovery Fallback
        t_mcp = time.time()
        risk_data = await self.call_mcp("construction.getLiveTelemetry", {
            "location": target_site,
            "intent": parsed.intent,
            "lat": mcp_ctx.coordinates.get("latitude") if mcp_ctx.coordinates else None,
            "lon": mcp_ctx.coordinates.get("longitude") if mcp_ctx.coordinates else None,
        })
        if risk_data:
            mcp_ctx.external_risk_data = risk_data
            # Log recovery to trace telemetry
            knowledge_context.found_context["mcp_recovered_thresholds"] = risk_data.get("thresholds", {})
            if "live_telemetry_reference" in risk_data:
                knowledge_context.found_context["live_telemetry_reference"] = risk_data["live_telemetry_reference"]

        ms_mcp = int((time.time() - t_mcp) * 1000)
        emit("step", "ConstructionAgent", "Phase III: Live Telemetry MCP", duration_ms=ms_mcp)

        # 5. Extract Weather Forecast Telemetry
        t_weather = time.time()
        forecast = await self.call_mcp("weather.getForecast", {
            "latitude": mcp_ctx.coordinates["latitude"],
            "longitude": mcp_ctx.coordinates["longitude"],
            "start_date": parsed.time_range.start,
            "end_date": parsed.time_range.end,
        })
        if forecast:
            mcp_ctx.weather_forecast = forecast

        ms_weather = int((time.time() - t_weather) * 1000)
        emit("step", "ConstructionAgent", "Phase IV: Weather Forecast MCP", duration_ms=ms_weather)

        # 6. Evaluate Operational Context Completeness markers
        has_recovered = "mcp_recovered_thresholds" in knowledge_context.found_context
        context_status = ContextStatus(
            knowledge_base_complete=False,
            mcp_called=True,
            missing_context_resolved=has_recovered,
            context_quality="usable_for_prediction" if has_recovered else "partial",
            trip_plan_ready=False,
            weather_optimization_ready=bool(mcp_ctx.weather_forecast),
        )

        return FullyProcessedPayload(
            domain=self.domain,
            intent=parsed.intent,
            intent_subtype=parsed.intent_subtype if hasattr(parsed, "intent_subtype") else "general",
            location=parsed.location,
            geographical_location=parsed.geographical_location,
            time_range=parsed.time_range,
            involved_context=involved_context,
            knowledge_context=knowledge_context,
            mcp_context=mcp_ctx,
            context_status=context_status,
            intelligence_requirements=IntelligenceRequirements(
                realtime_weather_needed=True,
                weather_variables=self.get_weather_variables(parsed.intent),
                reasoning_task=f"construction_{parsed.intent}",
            ),
            user_constraints=parsed.user_constraints,
            raw_user_input=parsed.raw_user_input,
        )