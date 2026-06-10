"""
MCP Route: place.searchPlaces
Phase 3.5: Uses TourismRetriever 3-tier (Qdrant strict → relaxed → Overpass live).
Returns V3 MCPResponseEnvelope.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from mcp.routes.envelope import make_envelope
from knowledge.retrievers.tourism_retriever import TourismRetriever

router = APIRouter()
_retriever = TourismRetriever()


class PlaceSearchRequest(BaseModel):
    location: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    category: Optional[str] = "tourist_attraction"
    limit: int = 20


@router.post("/searchPlaces")
async def search_places(req: PlaceSearchRequest) -> Dict[str, Any]:
    """
    Search tourist attractions using 3-tier KB retrieval:
      Tier 1 → Qdrant strict (score ≥ 0.72)
      Tier 2 → Qdrant relaxed (score ≥ 0.50)
      Tier 3 → Overpass OSM live fetch + async KB ingest
    """
    coordinates = {
        "latitude": req.lat or 16.0544,
        "longitude": req.lon or 108.2022,
    }

    result = await _retriever.get_attractions(
        location=req.location,
        coordinates=coordinates,
        limit=req.limit,
    )

    return make_envelope(
        route="place.searchPlaces",
        context_type="tourist_attractions",
        output={"attractions": result.data, "count": len(result.data)},
        provider=result.source,
        source_type="live" if result.source == "osm_live" else "static",
        freshness="live" if result.source == "osm_live" else "cached",
        input_data={"location": req.location, "lat": req.lat, "lon": req.lon, "limit": req.limit},
        warnings=result.warnings,
        errors=result.errors,
    )


@router.post("/getOpeningHours")
async def get_opening_hours(req: PlaceSearchRequest) -> Dict[str, Any]:
    """Return opening hours map {place_id: {day: hours}} from attraction data."""
    result = await _retriever.get_attractions(
        location=req.location,
        coordinates={"latitude": req.lat or 16.0544, "longitude": req.lon or 108.2022},
        limit=req.limit,
    )
    hours = {
        p["place_id"]: p.get("opening_hours", {"default": "07:00-17:00"})
        for p in result.data
        if "place_id" in p
    }
    return make_envelope(
        route="place.getOpeningHours",
        context_type="opening_hours",
        output={"opening_hours": hours, "count": len(hours)},
        provider=result.source,
        source_type="static",
        freshness="seeded",
        input_data={"location": req.location},
    )
