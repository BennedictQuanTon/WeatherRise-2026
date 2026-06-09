"""
MCP Route: location.resolveCoordinates
Resolves a location string to lat/lon using Nominatim (OpenStreetMap).
Cache: 30 days (coordinates are stable).
"""
import httpx
import hashlib
import json
import os
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

CACHE: dict = {}  # In-memory cache (Redis integration optional)


class LocationRequest(BaseModel):
    location: str


class LocationResponse(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    display_name: Optional[str] = None
    confidence: str = "low"
    source: str = "nominatim"
    cached: bool = False


@router.post("/resolveCoordinates", response_model=LocationResponse)
async def resolve_coordinates(req: LocationRequest):
    cache_key = f"loc:{req.location.lower().strip()}"

    if cache_key in CACHE:
        cached = CACHE[cache_key]
        cached["cached"] = True
        return LocationResponse(**cached)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": req.location, "format": "json", "limit": 1},
                headers={"User-Agent": "Weatherise/2.0 (hackathon@weatherise.ai)"},
            )
            r.raise_for_status()
            results = r.json()

        if not results:
            return LocationResponse(confidence="none", source="nominatim")

        top = results[0]
        result = {
            "latitude": float(top["lat"]),
            "longitude": float(top["lon"]),
            "display_name": top.get("display_name"),
            "confidence": "high",
            "source": "nominatim",
            "cached": False,
        }
        CACHE[cache_key] = result
        return LocationResponse(**result)

    except Exception as e:
        print(f"[MCP:location] Error: {e}")
        return LocationResponse(confidence="none", source="error")
