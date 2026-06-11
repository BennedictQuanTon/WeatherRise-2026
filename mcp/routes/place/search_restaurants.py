"""
MCP Route: place.searchRestaurants
Phase 2: Searches restaurants from PostgreSQL (Foody) with PostGIS proximity.
Falls back to danang_restaurants.json mock (with near_place_id links).
Returns V3 MCPResponseEnvelope.
"""
import os
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from mcp.routes.envelope import make_envelope

router = APIRouter()

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://weatherise:weatherise@localhost:5432/weatherise")
MOCK_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mcp_mock" / "tourism" / "danang_restaurants.json"


class RestaurantSearchRequest(BaseModel):
    location: str = "Da Nang"
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = 5.0
    near_place_id: Optional[str] = None   # Filter by attraction proximity
    category: Optional[str] = None
    vibe_tags: Optional[List[str]] = None
    price_tier: Optional[str] = None
    limit: int = 20


def _load_mock() -> List[Dict]:
    if MOCK_PATH.exists():
        with open(MOCK_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


async def _query_postgres(req: RestaurantSearchRequest) -> List[Dict]:
    try:
        import asyncpg
        conn = await asyncpg.connect(POSTGRES_URL)
        lat = req.lat or 16.0544
        lon = req.lon or 108.2022
        radius_m = req.radius_km * 1000

        query = """
            SELECT
                id, name_vi, name_en, category, sub_category,
                address, district, latitude, longitude,
                avg_rating, total_reviews, price_tier,
                vibe_tags, is_indoor, photo_url, foody_url,
                avg_duration_minutes, source,
                ST_Distance(coordinate, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS dist_m
            FROM locations
            WHERE category = 'restaurant'
            AND ST_DWithin(
                coordinate,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                $3
            )
            AND is_opening = true
            ORDER BY 
                CASE WHEN source = 'google_maps_scrape' THEN 0 ELSE 1 END ASC,
                dist_m ASC, 
                avg_rating DESC
            LIMIT $4
        """
        rows = await conn.fetch(query, lon, lat, radius_m, req.limit)
        await conn.close()

        return [
            {
                "place_id": r["id"],
                "name_vi": r["name_vi"],
                "name_en": r["name_en"],
                "category": "restaurant",
                "sub_category": r["sub_category"],
                "address": r["address"],
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "avg_rating": float(r["avg_rating"] or 0),
                "total_reviews": r["total_reviews"],
                "price_tier": r["price_tier"],
                "vibe_tags": list(r["vibe_tags"] or []),
                "is_indoor": r["is_indoor"],
                "photo_url": r["photo_url"],
                "avg_duration_minutes": r["avg_duration_minutes"],
                "distance_m": round(float(r["dist_m"]), 0),
                "source": r["source"] or "postgres_foody",
            }
            for r in rows
        ]
    except Exception as e:
        print(f"[MCP/searchRestaurants] PostgreSQL query failed: {e}")
        return []


@router.post("/searchRestaurants")
async def search_restaurants(req: RestaurantSearchRequest) -> Dict[str, Any]:
    """Search restaurants from Foody DB or mock. Returns V3 envelope."""
    results = await _query_postgres(req)
    provider = "postgres_foody"

    if not results:
        mock = _load_mock()
        # Optionally filter by near_place_id
        if req.near_place_id:
            nearby = [r for r in mock if r.get("near_place_id") == req.near_place_id]
            results = nearby or mock
        else:
            results = mock
        results = results[: req.limit]
        provider = "mock_fallback"

    warnings = []
    if provider == "mock_fallback":
        warnings.append("PostgreSQL unavailable — returning mock restaurant data.")

    return make_envelope(
        route="place.searchRestaurants",
        context_type="restaurants",
        output={"restaurants": results, "count": len(results)},
        provider=provider,
        source_type="dynamic" if provider == "postgres_foody" else "static",
        freshness="live" if provider == "postgres_foody" else "seeded",
        input_data={"location": req.location, "lat": req.lat, "lon": req.lon, "limit": req.limit},
        warnings=warnings,
    )
