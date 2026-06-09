"""
Construction Context Agent — Phase 4 Step 4
============================================
Domain-isolated LangGraph node for the Construction domain.

Execution plan (per context_agents_flow.md Step 4):
  1. Instantiate AgentExecutionPlan from extraction_key
  2. [Tier 1] Query Milvus construction_collection via nv-embedqa-e5-v5
     → On hit: populate ConstructionDomainSchema from metadata
     → On empty / timeout: fall through to Tier 2
  3. [Tier 2] Call Construction MCP server for live structural concrete logs
  4. Instantiate ConstructionDomainSchema from harvested data
  5. Wrap in ContextAgentPayload → validate → append to state
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..schemas.graph_state import WeatheriseGraphState
from ..schemas.domain_schemas import ConstructionDomainSchema, ContextAgentPayload
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
    path = base / "data" / "construction" / "danang_sites.json"

    try:
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        _SEED_CACHE = {r["site_id"]: r for r in records}
        for r in records:
            _SEED_CACHE[r["site_name"].lower()] = r
        logger.info("[CONSTRUCTION_AGENT] Seed data loaded | records=%d", len(records))
    except Exception as exc:
        logger.error("[CONSTRUCTION_AGENT] Seed data load failed: %s", exc)
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


def _build_construction_schema(raw: dict) -> ConstructionDomainSchema:
    return ConstructionDomainSchema(
        site_id=raw.get("site_id", "unknown"),
        site_name=raw.get("site_name", "Unknown Site"),
        city=raw.get("city", "Da Nang"),
        country=raw.get("country", "Vietnam"),
        lat=float(raw.get("lat", 16.054)),
        lon=float(raw.get("lon", 108.202)),
        project_type=raw.get("project_type", "unknown"),
        structural_safety_margin_mps=float(raw.get("structural_safety_margin_mps", 15.0)),
        max_rain_rate_mmh=float(raw.get("max_rain_rate_mmh", 25.0)),
        permit_status=raw.get("permit_status", "UNKNOWN"),
        last_concrete_pour_log=raw.get("last_concrete_pour_log"),
        restricted_weather_codes=raw.get("restricted_weather_codes", []),
    )


async def construction_context_agent(state: WeatheriseGraphState) -> WeatheriseGraphState:
    """
    Construction domain context agent — Step 4.

    Reads:  state["extraction_key"]
    Writes: state["context_payload"] (serialized ContextAgentPayload dict)
    """
    extraction_key: str = state["extraction_key"]
    execution_status = "SUCCESS_RAG"
    raw_data: Optional[dict] = None

    logger.info("[CONSTRUCTION_AGENT] Start | key=%s", extraction_key)

    # --- Tier 1: Milvus ---
    try:
        raw_data = await milvus_rag.query(
            collection=settings.MILVUS_CONSTRUCTION_COLLECTION,
            extraction_key=extraction_key,
        )
    except Exception as exc:
        logger.warning("[CONSTRUCTION_AGENT] Tier-1 exception: %s → Tier 2", exc)
        raw_data = None

    # --- Tier 2: MCP Fallback ---
    if raw_data is None:
        execution_status = "SUCCESS_MCP_FALLBACK"
        try:
            raw_data = await mcp_client.fetch_construction(extraction_key)
            logger.info("[CONSTRUCTION_AGENT] Tier-2 MCP hit | key=%s", extraction_key)
        except Exception as exc:
            logger.warning("[CONSTRUCTION_AGENT] Tier-2 MCP failed: %s → seed", exc)
            raw_data = None

    # --- Seed Fallback ---
    if raw_data is None:
        raw_data = _seed_lookup(extraction_key)
        if raw_data:
            logger.info("[CONSTRUCTION_AGENT] Seed data hit | key=%s", extraction_key)
        else:
            logger.error("[CONSTRUCTION_AGENT] All tiers exhausted | key=%s", extraction_key)
            return {
                **state,
                "error_detail": f"Construction context agent: no data found for key='{extraction_key}'",
            }

    # --- Schema Population ---
    construction_schema = _build_construction_schema(raw_data)

    # --- Envelope Assembly ---
    payload = ContextAgentPayload(
        execution_status=execution_status,
        active_domain="construction",
        tourism=None,
        fishery=None,
        construction=construction_schema,
    )

    # --- Terminal Handoff validation ---
    validated_payload = payload_validator.validate(payload)

    logger.info(
        "[CONSTRUCTION_AGENT] Complete | status=%s | site=%s",
        execution_status,
        construction_schema.site_id,
    )

    return {
        **state,
        "context_payload": validated_payload.model_dump(),
    }
