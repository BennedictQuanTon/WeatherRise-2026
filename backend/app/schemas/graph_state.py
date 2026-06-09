"""
LangGraph Global State Container — Phase 4
==========================================
Single TypedDict shared across all nodes in the StateGraph.
All writes are synchronous; no node mutates another node's already-written keys.
"""

from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict


class WeatheriseGraphState(TypedDict):
    """
    Immutable contract for the single execution token that traverses the graph.

    Populated progressively as execution flows through each node:
      - raw_input        → set by the API router before graph invocation
      - primary_intent   → set by discriminator_node (Step 2)
      - routing_confidence → set by discriminator_node (Step 2)
      - extraction_key   → set by discriminator_node (Step 2)
      - context_payload  → set by context agent node (Step 4)
      - error_detail     → set by error_handler_node on failure paths
    """

    raw_input: str
    """Sanitized string token from the GR-In gate. Immutable after handoff."""

    primary_intent: str
    """
    Resolved intent from the Discriminator.
    Allowed values: 'tourism' | 'fishery' | 'construction' | 'REJECT_OUT_OF_SCOPE'
    """

    routing_confidence: float
    """Confidence score [0.0, 1.0]. Values below threshold route to error_handler."""

    extraction_key: str
    """Localized entity parameter — site index, place name, or coordinate string."""

    context_payload: Optional[dict]
    """
    Serialized ContextAgentPayload dict appended after Step 4.2.
    Locked against mutation once written. None until context agent completes.
    """

    error_detail: Optional[str]
    """
    Human-readable error token set by error_handler_node.
    None on successful execution paths.
    """
