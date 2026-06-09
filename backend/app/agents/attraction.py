"""
Tourism Context Agent — Phase 4 Step 4
=======================================
Domain-isolated LangGraph node for the Tourism domain.

Execution plan (per context_agents_flow.md Step 4):
  1. Instantiate AgentExecutionPlan from extraction_key
  2. [Tier 1] Query Milvus tourism_collection via nv-embedqa-e5-v5
     → On hit: populate TourismDomainSchema from metadata
     → On empty / timeout: fall through to Tier 2
  3. [Tier 2] Call Tourism MCP server for live scheduling/capacity data
  4. Instantiate TourismDomainSchema from harvested data
  5. Wrap in ContextAgentPayload → validate → append to state
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..schemas.graph_state import WeatheriseGraphState
from ..schemas.domain_schemas import TourismDomainSchema, ContextAgentPayload
from ..services.rag import milvus_rag
from ..services.mcp_client import mcp_client
from ..services.payload_validator import payload_validator
from ..configs.settings import settings

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Seed data loader (static fallback when both Milvus and MCP are unavailable)
# ---------------------------------------------------------------------------
_SEED_CACHE: Optional[dict] = None


def _load_seed_data() -> dict:
    """Load danang_locations.json into memory, keyed by destination_id and name."""
    global _SEED_CACHE
    if _SEED_CACHE is not None:
        return _SEED_CACHE

    # Ascend from agents/ → app/ → backend/ → project root → data/
    base = Path(__file__).resolve().parent.parent.parent.parent
    path = base / "data" / "attractions" / "danang_locations.json"

    try:
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        _SEED_CACHE = {r["destination_id"]: r for r in records}
        # Also index by lowercased name for fuzzy match
        for r in records:
            _SEED_CACHE[r["name"].lower()] = r
        logger.info("[TOURISM_AGENT] Seed data loaded | records=%d", len(records))
    except Exception as exc:
        logger.error("[TOURISM_AGENT] Seed data load failed: %s", exc)
        _SEED_CACHE = {}

    return _SEED_CACHE


def _seed_lookup(extraction_key: str) -> Optional[dict]:
    """Find the best match for extraction_key in seed data."""
    seed = _load_seed_data()
    key_lower = extraction_key.lower().strip()

    # Exact ID match
    if key_lower in seed:
        return seed[key_lower]

    # Partial name match
    for k, v in seed.items():
        if key_lower in k or k in key_lower:
            return v

    return None


def _build_tourism_schema(raw: dict) -> TourismDomainSchema:
    """Map raw dict (from Milvus metadata, MCP response, or seed) → TourismDomainSchema."""
    return TourismDomainSchema(
        site_id=raw.get("destination_id", raw.get("site_id", "unknown")),
        site_name=raw.get("name", raw.get("site_name", "Unknown")),
        city=raw.get("city", "Da Nang"),
        country=raw.get("country", "Vietnam"),
        lat=float(raw.get("lat", 16.0544)),
        lon=float(raw.get("lon", 108.2022)),
        activity_type=raw.get("activity_type", "unknown"),
        tags=raw.get("tags", []),
        bad_weather_conditions=raw.get("bad_conditions", raw.get("bad_weather_conditions", [])),
        safe_alternative_ids=raw.get("safe_alternatives", raw.get("safe_alternative_ids", [])),
        operating_hours=raw.get("operating_hours"),
        max_capacity=raw.get("max_capacity"),
    )


async def tourism_context_agent(state: WeatheriseGraphState) -> WeatheriseGraphState:
    """
    Tourism domain context agent — Step 4.

    Reads:  state["extraction_key"]
    Writes: state["context_payload"] (serialized ContextAgentPayload dict)
    """
    extraction_key: str = state["extraction_key"]
    execution_status = "SUCCESS_RAG"
    raw_data: Optional[dict] = None

    logger.info("[TOURISM_AGENT] Start | key=%s", extraction_key)

    # --- Tier 1: Milvus Vector Search ---
    try:
        raw_data = await milvus_rag.query(
            collection=settings.MILVUS_TOURISM_COLLECTION,
            extraction_key=extraction_key,
        )
    except Exception as exc:
        logger.warning("[TOURISM_AGENT] Tier-1 exception: %s → Tier 2", exc)
        raw_data = None

    # --- Tier 2: MCP Fallback ---
    if raw_data is None:
        execution_status = "SUCCESS_MCP_FALLBACK"
        try:
            raw_data = await mcp_client.fetch_tourism(extraction_key)
            logger.info("[TOURISM_AGENT] Tier-2 MCP hit | key=%s", extraction_key)
        except Exception as exc:
            logger.warning(
                "[TOURISM_AGENT] Tier-2 MCP failed: %s → seed fallback", exc
            )
            raw_data = None

    # --- Seed Fallback (dev only) ---
    if raw_data is None:
        raw_data = _seed_lookup(extraction_key)
        if raw_data:
            logger.info("[TOURISM_AGENT] Seed data hit | key=%s", extraction_key)
        else:
            logger.error("[TOURISM_AGENT] All tiers exhausted | key=%s", extraction_key)
            return {
                **state,
                "error_detail": f"Tourism context agent: no data found for key='{extraction_key}'",
            }

    # --- Schema Population (Step 4: Polymorphic Serialization) ---
    tourism_schema = _build_tourism_schema(raw_data)

    # --- Envelope Assembly (Step 4: Envelope Assembly) ---
    payload = ContextAgentPayload(
        execution_status=execution_status,
        active_domain="tourism",
        tourism=tourism_schema,
        fishery=None,
        construction=None,
    )

    # --- Terminal Handoff validation (Step 4.2) ---
    validated_payload = payload_validator.validate(payload)

    logger.info(
        "[TOURISM_AGENT] Complete | status=%s | site=%s",
        execution_status,
        tourism_schema.site_id,
    )

    return {
        **state,
        "context_payload": validated_payload.model_dump(),
    }
