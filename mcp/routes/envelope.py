"""
MCP Response Envelope — V3 Standard Contract
All MCP routes must return this structure so the Context Fusion Layer
can reliably parse, normalize, and validate every tool response.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime


class MCPSource(BaseModel):
    provider: str                          # "local_seed" | "postgres_foody" | "osm_live" | "open-meteo" | "nominatim"
    source_type: str = "static"            # "static" | "dynamic" | "live"
    freshness: str = "cached"             # "live" | "cached" | "seeded"
    retrieved_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class MCPResponseEnvelope(BaseModel):
    route: str                             # e.g. "place.searchPlaces"
    context_type: str                      # e.g. "tourist_attractions"
    status: Literal["success", "partial", "error"]
    source: MCPSource
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []


def make_envelope(
    route: str,
    context_type: str,
    output: Dict[str, Any],
    provider: str,
    source_type: str = "static",
    freshness: str = "cached",
    input_data: Dict[str, Any] = {},
    errors: List[str] = [],
    warnings: List[str] = [],
) -> Dict[str, Any]:
    """Helper to build a standard MCP response dict."""
    status = "error" if errors else ("partial" if warnings else "success")
    return MCPResponseEnvelope(
        route=route,
        context_type=context_type,
        status=status,
        source=MCPSource(
            provider=provider,
            source_type=source_type,
            freshness=freshness,
        ),
        input=input_data,
        output=output,
        errors=errors,
        warnings=warnings,
    ).model_dump()
