"""
LangGraph StateGraph Assembly — Phase 4
========================================
Assembles the full single-domain routing graph from all agent nodes and the
conditional edge. Exposes a compiled, ready-to-invoke graph instance.

Graph topology:
    [ENTRY] → discriminator_node
              ↓ (conditional edge: routing_edge)
    ┌─────────┬──────────────┬────────────────────┐
    ▼         ▼              ▼                    ▼
 tourism  fishery     construction          error_handler
 _context _context    _context_agent            ↓
 _agent   _agent           ↓                   END
    ↓         ↓            END
   END       END

State persistence:
  - Primary: LangGraph in-memory state (StateGraph default)
  - Fallback: Redis-backed MemorySaver checkpoint if REDIS_URL is reachable
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..schemas.graph_state import WeatheriseGraphState
from .orchestrator import discriminator_node
from .router import routing_edge
from .attraction import tourism_context_agent
from .fishery import fishery_context_agent
from .construction import construction_context_agent

logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# Error Handler Node
# ---------------------------------------------------------------------------

async def error_handler_node(state: WeatheriseGraphState) -> WeatheriseGraphState:
    """
    Terminal error handler — receives all REJECT_OUT_OF_SCOPE and low-confidence routes.
    Writes a structured error_detail string and terminates graph execution.
    """
    intent = state.get("primary_intent", "UNKNOWN")
    confidence = state.get("routing_confidence", 0.0)
    existing_detail = state.get("error_detail")

    if existing_detail:
        error_msg = existing_detail
    elif intent == "REJECT_OUT_OF_SCOPE":
        error_msg = "OUT_OF_SCOPE: Query does not match any certified domain (tourism/fishery/construction)."
    else:
        error_msg = (
            f"LOW_CONFIDENCE: Routing confidence {confidence:.3f} below threshold. "
            "Query is ambiguous or does not clearly identify a domain entity."
        )

    logger.warning(
        "[ERROR_HANDLER] Graph terminated | intent=%s | confidence=%.3f | detail=%s",
        intent,
        confidence,
        error_msg,
    )

    return {**state, "error_detail": error_msg}


# ---------------------------------------------------------------------------
# Checkpointer — StateGraph primary, Redis fallback
# ---------------------------------------------------------------------------

def _build_checkpointer():
    """
    Attempt to create a Redis-backed checkpointer for state persistence.
    Falls back to in-memory MemorySaver if Redis is unavailable.
    """
    try:
        from langgraph.checkpoint.redis import RedisSaver
        from ..configs.settings import settings

        checkpointer = RedisSaver.from_conn_string(settings.REDIS_URL)
        logger.info("[GRAPH] Redis checkpointer active | url=%s", settings.REDIS_URL)
        return checkpointer
    except Exception as exc:
        logger.warning(
            "[GRAPH] Redis checkpointer unavailable (%s) — using in-memory MemorySaver",
            exc,
        )
        return MemorySaver()


# ---------------------------------------------------------------------------
# Graph Assembly
# ---------------------------------------------------------------------------

def build_graph():
    """
    Construct and compile the Weatherise Phase 4 StateGraph.

    Node registration order:
      1. discriminator (entry point)
      2. Three domain context agents
      3. error_handler (terminal sink)

    Conditional edge: routing_edge maps discriminator output → one of four nodes.
    Each context agent and error_handler terminate at END.
    """
    graph = StateGraph(WeatheriseGraphState)

    # Register nodes
    graph.add_node("discriminator", discriminator_node)
    graph.add_node("tourism_context_agent", tourism_context_agent)
    graph.add_node("fishery_context_agent", fishery_context_agent)
    graph.add_node("construction_context_agent", construction_context_agent)
    graph.add_node("error_handler", error_handler_node)

    # Entry point
    graph.set_entry_point("discriminator")

    # Conditional edge — Step 3: exactly one target, zero parallel threads
    graph.add_conditional_edges(
        "discriminator",
        routing_edge,
        {
            "tourism_context_agent": "tourism_context_agent",
            "fishery_context_agent": "fishery_context_agent",
            "construction_context_agent": "construction_context_agent",
            "error_handler": "error_handler",
        },
    )

    # Each leaf node terminates at END
    graph.add_edge("tourism_context_agent", END)
    graph.add_edge("fishery_context_agent", END)
    graph.add_edge("construction_context_agent", END)
    graph.add_edge("error_handler", END)

    # Compile with checkpointer
    checkpointer = _build_checkpointer()
    compiled = graph.compile(checkpointer=checkpointer)

    logger.info("[GRAPH] StateGraph compiled | nodes=5 | edges=conditional+4xEND")
    return compiled


# Module-level compiled graph instance
weatherise_graph = build_graph()
