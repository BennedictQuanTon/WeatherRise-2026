"""
MCP Route: location.resolveCoordinates
Phase 2: Resolves a location string to lat/lon using Nominatim (OSM).
Returns V3 MCPResponseEnvelope. Cache: 30 days (coordinates stable).
"""
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from mcp.routes.envelope import make_envelope

router = APIRouter()

CACHE: Dict[str, Any] = {}   # In-memory (Redis optional)

# Known city coordinates for fast offline fallback
_KNOWN_COORDS = {
    "da nang": {"latitude": 16.0544, "longitude": 108.2022, "display_name": "Đà Nẵng, Vietnam"},
    "da nẵng": {"latitude": 16.0544, "longitude": 108.2022, "display_name": "Đà Nẵng, Vietnam"},
    "hoi an": {"latitude": 15.8801, "longitude": 108.3380, "display_name": "Hội An, Quảng Nam, Vietnam"},
    "hội an": {"latitude": 15.8801, "longitude": 108.3380, "display_name": "Hội An, Quảng Nam, Vietnam"},
    "hanoi": {"latitude": 21.0285, "longitude": 105.8542, "display_name": "Hà Nội, Vietnam"},
    "hà nội": {"latitude": 21.0285, "longitude": 105.8542, "display_name": "Hà Nội, Vietnam"},
    "ho chi minh city": {"latitude": 10.7769, "longitude": 106.7009, "display_name": "TP. Hồ Chí Minh, Vietnam"},
    "sapa": {"latitude": 22.3364, "longitude": 103.8438, "display_name": "Sa Pa, Lào Cai, Vietnam"},
    "sa pa": {"latitude": 22.3364, "longitude": 103.8438, "display_name": "Sa Pa, Lào Cai, Vietnam"},
    "nha trang": {"latitude": 12.2388, "longitude": 109.1967, "display_name": "Nha Trang, Khánh Hòa, Vietnam"},
    "phu quoc": {"latitude": 10.2899, "longitude": 103.9840, "display_name": "Phú Quốc, Kiên Giang, Vietnam"},
}


class LocationRequest(BaseModel):
    location: str


@router.post("/resolveCoordinates")
async def resolve_coordinates(req: LocationRequest) -> Dict[str, Any]:
    key = req.location.lower().strip()
    cache_key = f"loc:{key}"

    if cache_key in CACHE:
        cached = CACHE[cache_key]
        return make_envelope(
            route="location.resolveCoordinates",
            context_type="coordinates",
            output={**cached, "cached": True},
            provider="nominatim",
            freshness="cached",
            input_data={"location": req.location},
        )

    # Fast path: known cities
    for known_key, result in _KNOWN_COORDS.items():
        if known_key in key:
            CACHE[cache_key] = result
            return make_envelope(
                route="location.resolveCoordinates",
                context_type="coordinates",
                output={**result, "confidence": "high", "cached": False},
                provider="known_coords",
                source_type="static",
                freshness="seeded",
                input_data={"location": req.location},
            )

    # Nominatim live lookup
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": req.location, "format": "json", "limit": 1},
                headers={"User-Agent": "Weatherise/3.0 (hackathon@weatherise.ai)"},
            )
            r.raise_for_status()
            results = r.json()

        if not results:
            return make_envelope(
                route="location.resolveCoordinates",
                context_type="coordinates",
                output={"confidence": "none"},
                provider="nominatim",
                freshness="live",
                input_data={"location": req.location},
                errors=[f"Location not found: {req.location}"],
            )

        top = results[0]
        result = {
            "latitude": float(top["lat"]),
            "longitude": float(top["lon"]),
            "display_name": top.get("display_name"),
            "confidence": "high",
            "cached": False,
        }
        CACHE[cache_key] = result
        return make_envelope(
            route="location.resolveCoordinates",
            context_type="coordinates",
            output=result,
            provider="nominatim",
            freshness="live",
            input_data={"location": req.location},
        )

    except Exception as e:
        print(f"[MCP:location] Error: {e}")
        return make_envelope(
            route="location.resolveCoordinates",
            context_type="coordinates",
            output={"confidence": "none"},
            provider="nominatim",
            freshness="live",
            input_data={"location": req.location},
            errors=[str(e)],
        )

