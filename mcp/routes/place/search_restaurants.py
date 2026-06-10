"""
MCP Route: place.searchRestaurants
Searches restaurants from PostgreSQL (Foody data) using PostGIS proximity.
Falls back to local seed JSON if DB unavailable.
"""
import os
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter()

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://weatherise:weatherise@localhost:5432/weatherise")
MOCK_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mcp_mock" / "tourism" / "danang_restaurants.json"


class RestaurantSearchRequest(BaseModel):
    location: str = "Da Nang"
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = 5.0
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
                avg_duration_minutes,
                ST_Distance(coordinate, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography) AS dist_m
            FROM locations
            WHERE category = 'restaurant'
            AND ST_DWithin(
                coordinate,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography,
                $3
            )
            AND is_opening = true
            ORDER BY dist_m ASC, avg_rating DESC
            LIMIT $4
        """
        rows = await conn.fetch(query, lon, lat, radius_m, req.limit)
        await conn.close()

        results = []
        for r in rows:
            results.append({
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
                "foody_url": r["foody_url"],
                "avg_duration_minutes": r["avg_duration_minutes"],
                "distance_m": round(float(r["dist_m"]), 0),
            })
        return results
    except Exception as e:
        print(f"[MCP/searchRestaurants] PostgreSQL query failed: {e}")
        return []


@router.post("/searchRestaurants")
async def search_restaurants(req: RestaurantSearchRequest):
    """Search restaurants from Foody DB with PostGIS proximity. Falls back to mock."""
    results = await _query_postgres(req)

    if results:
        return {"results": results, "source": "postgres_foody", "count": len(results)}

    # Fallback to mock data
    mock = _load_mock()
    if mock:
        return {"results": mock[:req.limit], "source": "mock_fallback", "count": len(mock[:req.limit])}

    return {"results": [], "source": "none", "count": 0}
