"""
Chat Router — Phase 4 API Entry Point
======================================
POST /chat — the single external API surface for the full agent pipeline.

Request flow:
  1. Receive ChatRequest (user_message + session_id)
  2. GR-In gate: GuardrailsGate.validate() → sanitized string or 403
  3. Build initial WeatheriseGraphState
  4. Invoke weatherise_graph.ainvoke() with thread config (session_id as thread_id)
  5. Return ContextAgentPayload or structured error to caller
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..models.request_schema import ChatRequest
from ..schemas.graph_state import WeatheriseGraphState
from ..services.guardrails_service import GuardrailsGate, GateRejectionError
from ..agents.graph import weatherise_graph

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/chat", tags=["Chat"])

_guardrails_gate = GuardrailsGate()


@router.post("", response_class=JSONResponse)
async def chat(request: ChatRequest):
    """
    Primary entry point for the Phase 4 agent pipeline.

    Step 1 — GR-In Gate:
        Validates the raw user message through NeMo Guardrails.
        Returns 403 if any rail fires (injection, jailbreak, off-topic).

    Steps 2–4 — LangGraph Execution:
        Invokes the compiled StateGraph with the sanitized token.
        The graph executes discriminator → router edge → context agent → END.

    Response:
        On success: serialized ContextAgentPayload dict with execution_status
        On gate rejection: 403 with refusal reason
        On graph error: 422 with error_detail from error_handler node
    """
    # --- Step 1: GR-In Gate ---
    try:
        sanitized_input = await _guardrails_gate.validate(request.user_message)
    except GateRejectionError as exc:
        logger.warning(
            "[CHAT] Gate rejection | session=%s | reason=%s",
            request.session_id,
            exc.reason,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "GATE_REJECTION",
                "reason": exc.reason,
                "session_id": request.session_id,
            },
        )

    # --- Steps 2–4: LangGraph Execution ---
    initial_state: WeatheriseGraphState = {
        "raw_input": sanitized_input,
        "primary_intent": "",
        "routing_confidence": 0.0,
        "extraction_key": "",
        "context_payload": None,
        "error_detail": None,
    }

    # Thread config uses session_id as LangGraph thread_id for state continuity
    config = {"configurable": {"thread_id": request.session_id}}

    try:
        logger.info(
            "[CHAT] Invoking graph | session=%s | input_preview=%.80s",
            request.session_id,
            sanitized_input,
        )

        final_state: WeatheriseGraphState = await weatherise_graph.ainvoke(
            initial_state, config=config
        )

    except Exception as exc:
        logger.error("[CHAT] Graph invocation failed | session=%s | error=%s", request.session_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "GRAPH_EXECUTION_FAILURE", "detail": str(exc)},
        )

    # --- Response Assembly ---
    error_detail = final_state.get("error_detail")
    context_payload = final_state.get("context_payload")

    if error_detail and not context_payload:
        # Graph routed to error_handler
        raise HTTPException(
            status_code=422,
            detail={
                "error": "ROUTING_REJECTION",
                "detail": error_detail,
                "primary_intent": final_state.get("primary_intent"),
                "routing_confidence": final_state.get("routing_confidence"),
                "session_id": request.session_id,
            },
        )

    logger.info(
        "[CHAT] Success | session=%s | domain=%s | status=%s",
        request.session_id,
        context_payload.get("active_domain") if context_payload else "N/A",
        context_payload.get("execution_status") if context_payload else "N/A",
    )

    return JSONResponse(
        content={
            "session_id": request.session_id,
            "primary_intent": final_state.get("primary_intent"),
            "routing_confidence": final_state.get("routing_confidence"),
            "extraction_key": final_state.get("extraction_key"),
            "context_payload": context_payload,
        }
    )
