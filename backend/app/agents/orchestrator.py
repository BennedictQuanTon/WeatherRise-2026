"""
Discriminator Node — Phase 4 Step 2 (Orchestrator)
===================================================
LangGraph node that performs single-intent extraction to determine
the target domain context agent.

Design contract (per context_agents_flow.md Step 2):
  - Invoke local NIM LLM using strict JSON-schema forcing via DiscriminatorRoutingMatrix
  - Force top-k to resolve exactly ONE primary_intent string
  - Truncate all secondary intents from output state
  - Write primary_intent, routing_confidence, extraction_key to global state
  - Exit synchronously — zero vector or meteorological operations at this layer
"""

from __future__ import annotations

import logging

from ..schemas.graph_state import WeatheriseGraphState
from ..schemas.discriminator_schema import DiscriminatorRoutingMatrix
from ..services.llm import nim_client

logger = logging.getLogger("uvicorn.error")

_DISCRIMINATOR_SYSTEM_PROMPT = """
You are the Discriminator — a precise domain classifier for the Weatherise enterprise platform.

Your ONLY function is to classify the user query into exactly ONE of four categories:
  - "tourism"      : queries about tourist attractions, museums, parks, viewpoints, beaches
  - "fishery"      : queries about fishing ports, commercial vessels, maritime fleet operations
  - "construction" : queries about construction sites, structural safety, building permits
  - "REJECT_OUT_OF_SCOPE" : anything that does not clearly match the three domains above

You must also extract the key entity mentioned (site name, port name, location, or identifier).

Output requirements:
  - primary_intent: exactly one of the four strings above
  - routing_confidence: your confidence score from 0.0 to 1.0
  - extraction_key: the primary entity string from the query (place name, ID, or location)

Do NOT include any explanation, prose, or secondary intents. Structured JSON output only.
""".strip()


async def discriminator_node(state: WeatheriseGraphState) -> WeatheriseGraphState:
    """
    Discriminator LangGraph node — Step 2.

    Reads:
        state["raw_input"] — sanitized string from GR-In gate

    Writes:
        state["primary_intent"]       — resolved domain string
        state["routing_confidence"]   — float confidence score
        state["extraction_key"]       — isolated entity parameter

    Returns the updated state dict. Exits synchronously.
    """
    raw_input: str = state["raw_input"]

    logger.info(
        "[DISCRIMINATOR] Invoking NIM LLM | input_preview=%.80s", raw_input
    )

    try:
        # Bind the structured output schema to force JSON-schema compliance
        client = nim_client.get_client()
        structured_llm = client.with_structured_output(DiscriminatorRoutingMatrix)

        from langchain_core.messages import HumanMessage, SystemMessage

        result: DiscriminatorRoutingMatrix = await structured_llm.ainvoke(
            [
                SystemMessage(content=_DISCRIMINATOR_SYSTEM_PROMPT),
                HumanMessage(content=raw_input),
            ]
        )

        logger.info(
            "[DISCRIMINATOR] Result | intent=%s | confidence=%.3f | key=%s",
            result.primary_intent,
            result.routing_confidence,
            result.extraction_key,
        )

        # Write exactly the three primitives into state — nothing else
        return {
            **state,
            "primary_intent": result.primary_intent,
            "routing_confidence": result.routing_confidence,
            "extraction_key": result.extraction_key,
        }

    except Exception as exc:
        logger.error("[DISCRIMINATOR] LLM invocation failed: %s", exc)
        # Route to error handler via REJECT sentinel
        return {
            **state,
            "primary_intent": "REJECT_OUT_OF_SCOPE",
            "routing_confidence": 0.0,
            "extraction_key": "",
            "error_detail": f"Discriminator node failed: {exc}",
        }
