"""
Pipeline Service — orchestrates the full Weatherise v2 flow:
  Raw Input → Parser → Orchestrator → Context Agent → KB → MCP → Intelligence Layer
"""
import sys
import os
import time

# Allow importing agents from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from agents.parser_agent.parser import LLMParser
from agents.orchestrator.orchestrator import Orchestrator
from agents.intelligence_layer.intelligence_service import IntelligenceService
from apps.api.app.routes.monitor import emit
from typing import AsyncIterator, Dict, Any

_parser = LLMParser()
_orchestrator = Orchestrator()
_intelligence = IntelligenceService()


async def run_pipeline(raw_input: str, session_id: str) -> Dict[str, Any]:
    """Pipeline with full timing + SSE emit to monitor."""
    pipeline_start = time.time()
    emit("info", "Pipeline", f"▶ [{session_id[:6]}] Start: {raw_input[:60]}")

    # Step 1: Parse
    t = time.time()
    emit("step", "Parser", "Calling NIM Nemotron 8B to parse input...")
    parsed = await _parser.parse(raw_input)
    ms = round((time.time() - t) * 1000)
    emit("success", "Parser", f"domain={parsed.domain} intent={parsed.intent} location={parsed.location}", ms)

    # Step 2: Route + fill context
    t = time.time()
    emit("step", "Orchestrator", f"Routing to {parsed.domain} context agent...")
    processed = await _orchestrator.run(parsed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Orchestrator", f"Context filled: {len(processed.involved_context)} items | MCP calls done", ms)

    # Step 3: Intelligence Layer
    t = time.time()
    emit("step", "Intelligence", "NIM reasoning with weather data + risk scoring...")
    result = await _intelligence.reason(processed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Intelligence", f"overall_risk={result.risk_assessment.overall_risk} | {result.prediction[:60]}", ms)

    total_ms = round((time.time() - pipeline_start) * 1000)
    emit("success", "Pipeline", f"✅ Complete in {total_ms}ms | domain={processed.domain} | loc={processed.location}", total_ms)

    return {
        "domain": processed.domain,
        "location": processed.location,
        "prediction": result.prediction,
        "recommendation": result.recommendation,
        "risk_assessment": result.risk_assessment.model_dump(),
        "explanation": result.explanation,
        "final_answer": result.final_answer,
    }


async def run_pipeline_streaming(
    raw_input: str, session_id: str
) -> AsyncIterator[Dict[str, Any]]:
    """WebSocket streaming — yields step events and also emits to SSE monitor."""
    pipeline_start = time.time()
    emit("info", "Pipeline", f"▶ WS [{session_id[:6]}] {raw_input[:60]}")

    yield {"type": "step", "step": "parsing", "data": {"message": "Analyzing your request..."}}
    t = time.time()
    emit("step", "Parser", "Calling NIM to parse input...")
    parsed = await _parser.parse(raw_input)
    ms = round((time.time() - t) * 1000)
    emit("success", "Parser", f"domain={parsed.domain} location={parsed.location}", ms)
    yield {"type": "step", "step": "parsed", "data": {
        "domain": parsed.domain, "intent": parsed.intent, "location": parsed.location,
    }}

    yield {"type": "step", "step": "routing", "data": {"message": f"Routing to {parsed.domain} agent..."}}
    t = time.time()
    emit("step", "Orchestrator", f"Routing → {parsed.domain} agent...")
    processed = await _orchestrator.run(parsed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Orchestrator", f"Context: {len(processed.involved_context)} items", ms)
    yield {"type": "step", "step": "context_filled", "data": {
        "involved_context": processed.involved_context,
    }}

    yield {"type": "step", "step": "reasoning", "data": {"message": "Generating weather intelligence..."}}
    t = time.time()
    emit("step", "Intelligence", "NIM reasoning...")
    result = await _intelligence.reason(processed)
    ms = round((time.time() - t) * 1000)
    emit("success", "Intelligence", f"risk={result.risk_assessment.overall_risk}", ms)

    total_ms = round((time.time() - pipeline_start) * 1000)
    emit("success", "Pipeline", f"✅ WS complete in {total_ms}ms", total_ms)

    yield {
        "type": "result",
        "data": {
            "domain": processed.domain,
            "location": processed.location,
            "prediction": result.prediction,
            "recommendation": result.recommendation,
            "risk_assessment": result.risk_assessment.model_dump(),
            "explanation": result.explanation,
            "final_answer": result.final_answer,
        }
    }
