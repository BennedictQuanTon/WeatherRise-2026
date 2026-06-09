"""
Conditional Edge — Phase 4 Step 3 (Switch-Block)
================================================
Deterministic LangGraph router function.

Design contract (per context_agents_flow.md Step 3):
  - Read ONLY from state — zero side effects
  - Return exactly ONE scalar string target node name
  - Zero concurrent threads — no parallel fan-out
  - Route to error_handler if primary_intent is REJECT or confidence < 0.70
"""

from __future__ import annotations

import logging

from ..schemas.graph_state import WeatheriseGraphState
from ..configs.settings import settings

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# String → node name mapping (Step 3: String-to-Node Mapping)
# ---------------------------------------------------------------------------
_INTENT_TO_NODE: dict[str, str] = {
    "tourism": "tourism_context_agent",
    "fishery": "fishery_context_agent",
    "construction": "construction_context_agent",
}


def routing_edge(state: WeatheriseGraphState) -> str:
    """
    Synchronous LangGraph router function — Step 3.

    Reads:
        state["primary_intent"]     — resolved domain string from discriminator
        state["routing_confidence"] — confidence score from discriminator

    Returns:
        Exactly one scalar string: the target node identifier.
        Never returns a list or dict. No parallel thread instantiation.

    Routing logic:
        1. REJECT_OUT_OF_SCOPE → "error_handler"
        2. confidence < ROUTING_CONFIDENCE_THRESHOLD → "error_handler"
        3. Valid intent → mapped context agent node name
    """
    primary_intent: str = state.get("primary_intent", "REJECT_OUT_OF_SCOPE")
    routing_confidence: float = state.get("routing_confidence", 0.0)
    threshold: float = settings.ROUTING_CONFIDENCE_THRESHOLD

    # Exception Redirection — Step 3: explicit REJECT
    if primary_intent == "REJECT_OUT_OF_SCOPE":
        logger.warning(
            "[ROUTER] Routing to error_handler | reason=REJECT_OUT_OF_SCOPE"
        )
        return "error_handler"

    # Exception Redirection — Step 3: confidence below threshold
    if routing_confidence < threshold:
        logger.warning(
            "[ROUTER] Routing to error_handler | reason=LOW_CONFIDENCE | "
            "confidence=%.3f | threshold=%.2f",
            routing_confidence,
            threshold,
        )
        return "error_handler"

    # String-to-Node Mapping — Step 3
    target_node = _INTENT_TO_NODE.get(primary_intent, "error_handler")

    logger.info(
        "[ROUTER] Routing token | intent=%s | confidence=%.3f → %s",
        primary_intent,
        routing_confidence,
        target_node,
    )

    return target_node
