"""
Pipeline Service — V3
Raw Input → Parser → Orchestrator → Context Agent → Intelligence Layer
Returns both weather prediction AND structured trip plan (if trip planning query).
"""
import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from agents.parser_agent.parser import LLMParser
from agents.orchestrator.orchestrator import Orchestrator
from agents.intelligence_layer.intelligence_service import IntelligenceService
from apps.api.app.routes.monitor import emit
from apps.api.app.schemas.response_schema import TripPlan, TripDay, TripStop
from typing import AsyncIterator, Dict, Any, Optional

_parser = LLMParser()
_orchestrator = Orchestrator()
_intelligence = IntelligenceService()


def _extract_trip_plan(processed) -> Optional[TripPlan]:
    """Convert mcp_context.trip_plan_context → TripPlan schema."""
    try:
        trip_data = None
        if hasattr(processed, "mcp_context") and processed.mcp_context:
            mcp = processed.mcp_context
            if hasattr(mcp, "trip_plan_context"):
                trip_data = mcp.trip_plan_context
            elif isinstance(mcp, dict):
                trip_data = mcp.get("trip_plan_context")

        if not trip_data:
            return None

        days = []
        for d in trip_data.get("days", []):
            stops = []
            for s in d.get("stops", []):
                stops.append(TripStop(
                    order=s.get("order", 1),
                    place_id=s.get("place_id", ""),
                    name=s.get("name", ""),
                    lat=s.get("lat", 16.054),
                    lon=s.get("lon", 108.202),
                    time_block=s.get("time_block", "morning"),
                    planned_time=s.get("planned_time", "08:00"),
                    forecast_temp=s.get("forecast_temp"),
                    weather_condition=s.get("weather_condition"),
                    duration_minutes=s.get("duration_minutes", 60),
                    is_indoor=s.get("is_indoor", False),
                    category=s.get("category", "attraction"),
                    vibe_tags=s.get("vibe_tags", []),
                ))
            days.append(TripDay(
                day=d.get("day", 1),
                theme=d.get("theme"),
                primary_area=d.get("primary_area", "Da Nang"),
                stops=stops,
                backup_options=d.get("backup_options", []),
            ))

        return TripPlan(
            duration_days=trip_data.get("duration_days", len(days)),
            location=trip_data.get("location", processed.location or "Da Nang"),
            days=days,
            weather_aware=bool(getattr(processed, "mcp_context", None) and
                               getattr(processed.mcp_context, "weather_forecast", None)),
            planning_mode=trip_data.get("planning_mode", "heuristic_v3"),
        )
    except Exception as e:
        print(f"[Pipeline] Trip plan extraction error: {e}")
        return None


async def run_pipeline(raw_input: str, session_id: str) -> Dict[str, Any]:
    pipeline_start = time.time()
    emit("info", "Pipeline", f"▶ [{session_id[:6]}] Start: {raw_input[:60]}")

    # Step 1: Parse
    t = time.time()
    emit("step", "Parser", "Calling NIM to parse input...")
    parsed = await _parser.parse(raw_input)
    ms = round((time.time() - t) * 1000)
    emit("success", "Parser",
         f"domain={parsed.domain} intent={parsed.intent} subtype={parsed.intent_subtype} loc={parsed.location}", ms)

    # Step 2: Orchestrate + context
    t = time.time()
    emit("step", "Orchestrator", f"Routing to {parsed.domain} context agent...")
    processed = await _orchestrator.run(parsed)
    ms = round((time.time() - t) * 1000)
    is_trip = parsed.intent_subtype == "multi_day_trip_planning"
    emit("success", "Orchestrator",
         f"context={len(processed.involved_context)} items | trip_plan={is_trip}", ms)

    # Step 3: Intelligence Layer
    t = time.time()
    emit("step", "Intelligence", "NIM reasoning with weather + trip context...")
    result = await _intelligence.reason(processed)
    ms = round((time.time() - t) * 1000)
    risk_summary = ", ".join(f"{k}={v}" for k, v in result.risk_assessment.items())
    emit("success", "Intelligence", f"{risk_summary}", ms)

    # Extract structured trip plan
    trip_plan = _extract_trip_plan(processed) if is_trip else None

    total_ms = round((time.time() - pipeline_start) * 1000)
    emit("success", "Pipeline",
         f"✅ Complete in {total_ms}ms | domain={processed.domain} | trip={trip_plan is not None}", total_ms)

    return {
        "domain": processed.domain,
        "location": processed.location,
        "intent_subtype": parsed.intent_subtype,
        "prediction": result.prediction,
        "recommendation": result.recommendation,
        "risk_assessment": {k: v.value if hasattr(v, "value") else v for k, v in result.risk_assessment.items()},
        "explanation": result.explanation,
        "final_answer": result.final_answer,
        "metadata": result.metadata,
        "trip_plan": trip_plan.model_dump() if trip_plan else None,
    }


async def run_pipeline_streaming(
    raw_input: str, session_id: str
) -> AsyncIterator[Dict[str, Any]]:
    pipeline_start = time.time()
    emit("info", "Pipeline", f"▶ WS [{session_id[:6]}] {raw_input[:60]}")

    yield {"type": "step", "step": "parsing", "data": {"message": "Analyzing your request..."}}
    t = time.time()
    parsed = await _parser.parse(raw_input)
    ms = round((time.time() - t) * 1000)
    emit("success", "Parser", f"domain={parsed.domain} subtype={parsed.intent_subtype}", ms)
    yield {"type": "step", "step": "parsed", "data": {
        "domain": parsed.domain,
        "intent": parsed.intent,
        "intent_subtype": parsed.intent_subtype,
        "location": parsed.location,
    }}

    yield {"type": "step", "step": "routing", "data": {"message": f"Routing to {parsed.domain} agent..."}}
    t = time.time()
    processed = await _orchestrator.run(parsed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Orchestrator", f"Context: {len(processed.involved_context)} items", ms)
    yield {"type": "step", "step": "context_filled", "data": {
        "involved_context": processed.involved_context,
    }}

    yield {"type": "step", "step": "reasoning", "data": {"message": "Generating weather intelligence..."}}
    t = time.time()
    result = await _intelligence.reason(processed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Intelligence", f"reasoning done in {ms}ms", ms)

    is_trip = parsed.intent_subtype == "multi_day_trip_planning"
    trip_plan = _extract_trip_plan(processed) if is_trip else None
    total_ms = round((time.time() - pipeline_start) * 1000)
    emit("success", "Pipeline", f"✅ WS complete in {total_ms}ms", total_ms)

    yield {
        "type": "result",
        "data": {
            "domain": processed.domain,
            "location": processed.location,
            "intent_subtype": parsed.intent_subtype,
            "prediction": result.prediction,
            "recommendation": result.recommendation,
            "risk_assessment": {k: v.value if hasattr(v, "value") else v for k, v in result.risk_assessment.items()},
            "explanation": result.explanation,
            "final_answer": result.final_answer,
            "metadata": result.metadata,
            "trip_plan": trip_plan.model_dump() if trip_plan else None,
        }
    }
