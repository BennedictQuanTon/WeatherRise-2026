"""
Pipeline Service — orchestrates the full Weatherise v2 flow:
  Raw Input → Parser → Orchestrator → Context Agent → KB → MCP → Intelligence Layer
"""
import sys
import os

# Allow importing agents from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from agents.parser_agent.parser import LLMParser
from agents.orchestrator.orchestrator import Orchestrator
from agents.intelligence_layer.intelligence_service import IntelligenceService
from typing import AsyncIterator, Dict, Any

_parser = LLMParser()
_orchestrator = Orchestrator()
_intelligence = IntelligenceService()


async def run_pipeline(raw_input: str, session_id: str) -> Dict[str, Any]:
    """Synchronous-style pipeline returning final result dict."""

    # Step 1: Parse
    parsed = await _parser.parse(raw_input)

    # Step 2: Route to context agent + fill context
    processed = await _orchestrator.run(parsed)

    # Step 3: Intelligence Layer
    result = await _intelligence.reason(processed)

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
    """Generator that yields step events for WebSocket streaming."""

    yield {"type": "step", "step": "parsing", "data": {"message": "Analyzing your request..."}}
    parsed = await _parser.parse(raw_input)
    yield {"type": "step", "step": "parsed", "data": {
        "domain": parsed.domain,
        "intent": parsed.intent,
        "location": parsed.location,
    }}

    yield {"type": "step", "step": "routing", "data": {"message": f"Routing to {parsed.domain} agent..."}}
    processed = await _orchestrator.run(parsed)
    yield {"type": "step", "step": "context_filled", "data": {
        "involved_context": processed.involved_context,
    }}

    yield {"type": "step", "step": "reasoning", "data": {"message": "Generating weather intelligence..."}}
    result = await _intelligence.reason(processed)

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
