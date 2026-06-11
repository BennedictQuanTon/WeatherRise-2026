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
                date=d.get("date"),
                weather_condition=d.get("weather_condition"),
                temp_range=d.get("temp_range"),
                rain_prob=d.get("rain_prob"),
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

    if parsed.domain == "unknown":
        emit("step", "Orchestrator", "Query rejected by Parser (Irrelevant domain).")
        emit("success", "Orchestrator", "Bypassed context agents.", 0)
        emit("success", "Pipeline", f"✅ Complete in {ms}ms | domain=unknown | trip=False", ms)
        return {
            "domain": "unknown",
            "location": parsed.location,
            "intent_subtype": parsed.intent_subtype,
            "prediction": "N/A",
            "recommendation": "I am a weather-risk intelligence assistant. I can help you with travel planning, construction safety, and agricultural weather impacts. Please ask a related query.",
            "risk_assessment": {"overall": "Low risk"},
            "explanation": "Query is outside my domain expertise.",
            "final_answer": "I am an AI assistant specialized in weather-risk intelligence for tourism, construction, and agriculture. Your query does not seem related to these domains. How can I help you with weather planning today?",
            "metadata": {},
            "trip_plan": None,
            "coordinates": None,
            "evidence": None,
            "weather_stats": None,
            "time_range": None,
            "weather_path": None,
            "weather_confidence": None,
            "weather_mode": None,
            "sources_used": None,
            "sources_rejected": None,
            "weather_debug": None,
        }

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

    coordinates = None
    if hasattr(processed, "geographical_location") and processed.geographical_location:
        coords = processed.geographical_location.coordinates
        if isinstance(coords, dict):
            coordinates = coords
        elif hasattr(coords, "model_dump"):
            coordinates = coords.model_dump()
    if not coordinates and hasattr(processed, "mcp_context") and processed.mcp_context:
        c_dict = processed.mcp_context if isinstance(processed.mcp_context, dict) else processed.mcp_context.model_dump()
        coordinates = c_dict.get("coordinates")

    evidence = result.metadata.get("evidence") if result.metadata else None
    weather_stats = result.metadata.get("weather_stats") if result.metadata else None
    weather_path = result.metadata.get("weather_path") if result.metadata else None
    weather_confidence = result.metadata.get("weather_confidence") if result.metadata else None
    weather_mode = result.metadata.get("weather_mode") if result.metadata else None
    sources_used = result.metadata.get("sources_used") if result.metadata else None
    sources_rejected = result.metadata.get("sources_rejected") if result.metadata else None
    weather_debug = result.metadata.get("weather_debug") if result.metadata else None

    time_range = None
    if hasattr(processed, "time_range") and processed.time_range:
        tr = processed.time_range
        time_range = {
            "start": tr.start if hasattr(tr, "start") else getattr(tr, "get")("start"),
            "end": tr.end if hasattr(tr, "end") else getattr(tr, "get")("end"),
        }

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
        "coordinates": coordinates,
        "evidence": evidence,
        "weather_stats": weather_stats,
        "time_range": time_range,
        "weather_path": weather_path,
        "weather_confidence": weather_confidence,
        "weather_mode": weather_mode,
        "sources_used": sources_used,
        "sources_rejected": sources_rejected,
        "weather_debug": weather_debug,
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

    if parsed.domain == "unknown":
        emit("step", "Orchestrator", "Query rejected by Parser (Irrelevant domain).")
        emit("success", "Orchestrator", "Bypassed context agents.", 0)
        emit("success", "Pipeline", f"✅ WS complete in {ms}ms | domain=unknown", ms)
        yield {
            "type": "result",
            "data": {
                "domain": "unknown",
                "location": parsed.location,
                "intent_subtype": parsed.intent_subtype,
                "prediction": "N/A",
                "recommendation": "I am a weather-risk intelligence assistant. I can help you with travel planning, construction safety, and agricultural weather impacts. Please ask a related query.",
                "risk_assessment": {"overall": "Low risk"},
                "explanation": "Query is outside my domain expertise.",
                "final_answer": "I am an AI assistant specialized in weather-risk intelligence for tourism, construction, and agriculture. Your query does not seem related to these domains. How can I help you with weather planning today?",
                "metadata": {},
                "trip_plan": None,
                "coordinates": None,
                "evidence": None,
                "weather_stats": None,
                "time_range": None,
                "weather_path": None,
                "weather_confidence": None,
                "weather_mode": None,
                "sources_used": None,
                "sources_rejected": None,
                "weather_debug": None,
            }
        }
        return

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

    coordinates = None
    if hasattr(processed, "geographical_location") and processed.geographical_location:
        coords = processed.geographical_location.coordinates
        if isinstance(coords, dict):
            coordinates = coords
        elif hasattr(coords, "model_dump"):
            coordinates = coords.model_dump()
    if not coordinates and hasattr(processed, "mcp_context") and processed.mcp_context:
        c_dict = processed.mcp_context if isinstance(processed.mcp_context, dict) else processed.mcp_context.model_dump()
        coordinates = c_dict.get("coordinates")

    evidence = result.metadata.get("evidence") if result.metadata else None
    weather_stats = result.metadata.get("weather_stats") if result.metadata else None
    weather_path = result.metadata.get("weather_path") if result.metadata else None
    weather_confidence = result.metadata.get("weather_confidence") if result.metadata else None
    weather_mode = result.metadata.get("weather_mode") if result.metadata else None
    sources_used = result.metadata.get("sources_used") if result.metadata else None
    sources_rejected = result.metadata.get("sources_rejected") if result.metadata else None
    weather_debug = result.metadata.get("weather_debug") if result.metadata else None

    time_range = None
    if hasattr(processed, "time_range") and processed.time_range:
        tr = processed.time_range
        time_range = {
            "start": tr.start if hasattr(tr, "start") else getattr(tr, "get")("start"),
            "end": tr.end if hasattr(tr, "end") else getattr(tr, "get")("end"),
        }

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
            "coordinates": coordinates,
            "evidence": evidence,
            "weather_stats": weather_stats,
            "time_range": time_range,
            "weather_path": weather_path,
            "weather_confidence": weather_confidence,
            "weather_mode": weather_mode,
            "sources_used": sources_used,
            "sources_rejected": sources_rejected,
            "weather_debug": weather_debug,
        }
    }
