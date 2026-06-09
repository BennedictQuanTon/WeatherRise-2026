"""
Domain Data Contract Schemas — Phase 4 Step 4 / 4.2
=====================================================
Three domain-isolated data models plus the unified ContextAgentPayload envelope.

Rules enforced by this module (per context_agents_flow.md Step 4.2):
  - Zero-prose: all string fields contain only raw parameters, never sentences.
  - Exclusivity: exactly one domain schema is non-null inside ContextAgentPayload.
  - Immutability: ContextAgentPayload is frozen post-assembly.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tourism Domain
# ---------------------------------------------------------------------------

class TourismDomainSchema(BaseModel):
    """Static + live parameters for a tourism site extracted from Milvus or MCP."""

    site_id: str = Field(..., description="Unique site index from the vector collection")
    site_name: str = Field(..., description="Official name of the tourism destination")
    city: str
    country: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    activity_type: str = Field(..., description="e.g. outdoor_nature, indoor_museum")
    tags: List[str] = Field(default_factory=list)
    bad_weather_conditions: List[str] = Field(
        default_factory=list,
        description="Weather condition codes that make this site unsafe",
    )
    safe_alternative_ids: List[str] = Field(
        default_factory=list,
        description="Destination IDs of safe indoor alternatives",
    )
    operating_hours: Optional[str] = Field(
        None, description="Raw operating hours string — no prose"
    )
    max_capacity: Optional[int] = Field(None, description="Max visitor capacity")


# ---------------------------------------------------------------------------
# Fishery Domain
# ---------------------------------------------------------------------------

class FisheryDomainSchema(BaseModel):
    """Live operational parameters for a commercial port or fishing fleet zone."""

    port_id: str = Field(..., description="Unique port identifier from the vector collection")
    port_name: str
    city: str
    country: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    port_type: str = Field(..., description="e.g. commercial_fishing, deep_sea_fleet")
    active_vessel_count: Optional[int] = Field(None, description="Live vessel count from MCP")
    berth_capacity: int = Field(..., description="Total berth slots available")
    fleet_status: str = Field(..., description="e.g. OPERATIONAL, RESTRICTED, CLOSED")
    restricted_weather_codes: List[str] = Field(
        default_factory=list,
        description="Weather condition codes requiring fleet recall",
    )
    safe_harbor_ids: List[str] = Field(
        default_factory=list,
        description="Alternative port IDs for emergency shelter",
    )


# ---------------------------------------------------------------------------
# Construction Domain
# ---------------------------------------------------------------------------

class ConstructionDomainSchema(BaseModel):
    """Structural safety parameters and live concrete logs for an active construction site."""

    site_id: str = Field(..., description="Unique construction site identifier")
    site_name: str
    city: str
    country: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    project_type: str = Field(
        ..., description="e.g. high_rise, bridge, coastal_infrastructure"
    )
    structural_safety_margin_mps: float = Field(
        ..., description="Max safe wind speed in m/s before work suspension"
    )
    max_rain_rate_mmh: float = Field(
        ..., description="Max safe rain rate in mm/h before suspension"
    )
    permit_status: str = Field(..., description="e.g. ACTIVE, SUSPENDED, EXPIRED")
    last_concrete_pour_log: Optional[str] = Field(
        None, description="ISO 8601 timestamp of the most recent pour — no prose"
    )
    restricted_weather_codes: List[str] = Field(
        default_factory=list,
        description="Weather codes triggering mandatory work suspension",
    )


# ---------------------------------------------------------------------------
# Unified Envelope
# ---------------------------------------------------------------------------

ExecutionStatus = Literal["SUCCESS_RAG", "SUCCESS_MCP_FALLBACK", "ERROR"]


class ContextAgentPayload(BaseModel):
    """
    Unified output envelope from any context agent node.

    Exclusivity contract: exactly one of the three domain fields is non-null.
    The other two must be explicitly set to None.

    Immutability: model is frozen — no field may be mutated after instantiation.
    """

    model_config = {"frozen": True}

    execution_status: ExecutionStatus = Field(
        ...,
        description="SUCCESS_RAG if Tier-1 Milvus hit, SUCCESS_MCP_FALLBACK if Tier-2 used",
    )
    active_domain: Literal["tourism", "fishery", "construction"] = Field(
        ..., description="The single domain whose schema is non-null"
    )

    tourism: Optional[TourismDomainSchema] = None
    fishery: Optional[FisheryDomainSchema] = None
    construction: Optional[ConstructionDomainSchema] = None
