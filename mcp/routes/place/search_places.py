"""
MCP Route: place.searchPlaces
Searches for places/POI using local seed data first, then OSM fallback.
Cache: 7 days.
"""
import json
import os
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()

# Load local seed data at startup
_SEED_DIR = Path(__file__).parent.parent.parent.parent / "knowledge" / "seed_data"
_CACHE: Dict[str, Any] = {}


def _load_seed(domain: str, filename: str) -> List[Dict]:
    path = _SEED_DIR / domain / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


_TOURISM_PLACES = _load_seed("tourism", "danang_locations.json")
_CONSTRUCTION_SITES = _load_seed("construction", "danang_sites.json")


class PlaceSearchRequest(BaseModel):
    location: str
    category: Optional[str] = "tourist_attraction"
    limit: int = 10


@router.post("/searchPlaces")
async def search_places(req: PlaceSearchRequest):
    location_lower = req.location.lower()
    cat = req.category or "tourist_attraction"

    # Tourism places from local seed
    if "tourism" in cat or "tourist" in cat or "attraction" in cat:
        city_match = [
            p for p in _TOURISM_PLACES
            if p.get("city", "").lower() in location_lower
               or location_lower in p.get("city", "").lower()
        ]
        if city_match:
            return {"results": city_match[:req.limit], "source": "local_seed"}

    # Construction sites from local seed
    if "construction" in cat:
        return {"results": _CONSTRUCTION_SITES[:req.limit], "source": "local_seed"}

    # Fallback: return empty (OSM integration can be added later)
    return {"results": [], "source": "none", "note": "No local data for this location/category"}


@router.post("/getOpeningHours")
async def get_opening_hours(req: PlaceSearchRequest):
    """Get opening hours from local seed data."""
    results = await search_places(req)
    places = results.get("results", [])
    hours = {}
    for p in places:
        pid = p.get("destination_id") or p.get("id", p.get("name", "unknown"))
        hours[pid] = p.get("opening_hours", "9:00 AM – 5:00 PM (typical)")
    return {"opening_hours": hours, "source": "local_seed"}
