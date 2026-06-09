"""
Fishery Context Agent — Phase 4 Step 4
=======================================
Domain-isolated LangGraph node for the Fishery / Commercial Fleet domain.

Execution plan (per context_agents_flow.md Step 4):
  1. Instantiate AgentExecutionPlan from extraction_key
  2. [Tier 1] Query Milvus fishery_collection via nv-embedqa-e5-v5
     → On hit: populate FisheryDomainSchema from metadata
     → On empty / timeout: fall through to Tier 2
  3. [Tier 2] Call Fishery MCP server for live port capacity / fleet status
  4. Instantiate FisheryDomainSchema from harvested data
  5. Wrap in ContextAgentPayload → validate → append to state
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..schemas.graph_state import WeatheriseGraphState
from ..schemas.domain_schemas import FisheryDomainSchema, ContextAgentPayload
from ..services.rag import milvus_rag
from ..services.mcp_client import mcp_client
from ..services.payload_validator import payload_validator
from ..configs.settings import settings

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Seed data loader
# ---------------------------------------------------------------------------
_SEED_CACHE: Optional[dict] = None


def _load_seed_data() -> dict:
    global _SEED_CACHE
    if _SEED_CACHE is not None:
        return _SEED_CACHE

    base = Path(__file__).resolve().parent.parent.parent.parent
    path = base / "data" / "fishery" / "danang_ports.json"

    try:
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        _SEED_CACHE = {r["port_id"]: r for r in records}
        for r in records:
            _SEED_CACHE[r["port_name"].lower()] = r
        logger.info("[FISHERY_AGENT] Seed data loaded | records=%d", len(records))
    except Exception as exc:
        logger.error("[FISHERY_AGENT] Seed data load failed: %s", exc)
        _SEED_CACHE = {}

    return _SEED_CACHE


def _seed_lookup(extraction_key: str) -> Optional[dict]:
    seed = _load_seed_data()
    key_lower = extraction_key.lower().strip()

    if key_lower in seed:
        return seed[key_lower]

    for k, v in seed.items():
        if key_lower in k or k in key_lower:
            return v

    return None


def _build_fishery_schema(raw: dict) -> FisheryDomainSchema:
    return FisheryDomainSchema(
        port_id=raw.get("port_id", "unknown"),
        port_name=raw.get("port_name", "Unknown Port"),
        city=raw.get("city", "Da Nang"),
        country=raw.get("country", "Vietnam"),
        lat=float(raw.get("lat", 16.107)),
        lon=float(raw.get("lon", 108.247)),
        port_type=raw.get("port_type", "commercial_fishing"),
        active_vessel_count=raw.get("active_vessel_count"),
        berth_capacity=int(raw.get("berth_capacity", 0)),
        fleet_status=raw.get("fleet_status", "UNKNOWN"),
        restricted_weather_codes=raw.get("restricted_weather_codes", []),
        safe_harbor_ids=raw.get("safe_harbor_ids", []),
    )


async def fishery_context_agent(state: WeatheriseGraphState) -> WeatheriseGraphState:
    """
    Fishery domain context agent — Step 4.

    Reads:  state["extraction_key"]
    Writes: state["context_payload"] (serialized ContextAgentPayload dict)
    """
    extraction_key: str = state["extraction_key"]
    execution_status = "SUCCESS_RAG"
    raw_data: Optional[dict] = None

    logger.info("[FISHERY_AGENT] Start | key=%s", extraction_key)

    # --- Tier 1: Milvus ---
    try:
        raw_data = await milvus_rag.query(
            collection=settings.MILVUS_FISHERY_COLLECTION,
            extraction_key=extraction_key,
        )
    except Exception as exc:
        logger.warning("[FISHERY_AGENT] Tier-1 exception: %s → Tier 2", exc)
        raw_data = None

    # --- Tier 2: MCP Fallback ---
    if raw_data is None:
        execution_status = "SUCCESS_MCP_FALLBACK"
        try:
            raw_data = await mcp_client.fetch_fishery(extraction_key)
            logger.info("[FISHERY_AGENT] Tier-2 MCP hit | key=%s", extraction_key)
        except Exception as exc:
            logger.warning("[FISHERY_AGENT] Tier-2 MCP failed: %s → seed", exc)
            raw_data = None

    # --- Seed Fallback ---
    if raw_data is None:
        raw_data = _seed_lookup(extraction_key)
        if raw_data:
            logger.info("[FISHERY_AGENT] Seed data hit | key=%s", extraction_key)
        else:
            logger.error("[FISHERY_AGENT] All tiers exhausted | key=%s", extraction_key)
            return {
                **state,
                "error_detail": f"Fishery context agent: no data found for key='{extraction_key}'",
            }

    # --- Schema Population ---
    fishery_schema = _build_fishery_schema(raw_data)

    # --- Envelope Assembly ---
    payload = ContextAgentPayload(
        execution_status=execution_status,
        active_domain="fishery",
        tourism=None,
        fishery=fishery_schema,
        construction=None,
    )

    # --- Terminal Handoff validation ---
    validated_payload = payload_validator.validate(payload)

    logger.info(
        "[FISHERY_AGENT] Complete | status=%s | port=%s",
        execution_status,
        fishery_schema.port_id,
    )

    return {
        **state,
        "context_payload": validated_payload.model_dump(),
    }
