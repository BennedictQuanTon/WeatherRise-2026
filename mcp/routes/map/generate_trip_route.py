"""
MCP Route: map.generateTripRoutePlan + map.getDistanceMatrix
Uses OSRM (self-hosted or demo) for distance matrix. Haversine fallback.
"""
import math
import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()

# OSRM: self-hosted preferred, fallback to demo
OSRM_URL = os.getenv("OSRM_BASE_URL", "http://osrm:5000")
OSRM_DEMO_URL = "http://router.project-osrm.org"


class Waypoint(BaseModel):
    place_id: str
    name: str
    lat: float
    lon: float


class DistanceMatrixRequest(BaseModel):
    waypoints: List[Waypoint]


class TripRoutePlanRequest(BaseModel):
    stops: List[Waypoint]
    duration_days: int = 1
    optimize: bool = True


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_osrm_matrix(coords: List[Dict]) -> Optional[Dict]:
    """Try OSRM table API. Returns durations in seconds."""
    coord_str = ";".join(f"{c['lon']},{c['lat']}" for c in coords)
    for base_url in [OSRM_URL, OSRM_DEMO_URL]:
        try:
            url = f"{base_url}/table/v1/driving/{coord_str}"
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(url, params={"annotations": "duration,distance"})
                r.raise_for_status()
                data = r.json()
                if data.get("code") == "Ok":
                    return data
        except Exception as e:
            print(f"[OSRM] {base_url} failed: {e}")
    return None


@router.post("/getDistanceMatrix")
async def get_distance_matrix(req: DistanceMatrixRequest):
    """Get travel time matrix between waypoints. OSRM → Haversine fallback."""
    coords = [{"lat": w.lat, "lon": w.lon} for w in req.waypoints]
    n = len(coords)

    osrm = await get_osrm_matrix(coords)
    if osrm:
        durations = osrm.get("durations", [])
        distances = osrm.get("distances", [])
        return {
            "source": "osrm",
            "waypoints": [w.dict() for w in req.waypoints],
            "duration_seconds": durations,
            "distance_meters": distances,
        }

    # Haversine fallback (seconds estimate: assume avg 30 km/h city speed)
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            km = haversine_km(coords[i]["lat"], coords[i]["lon"], coords[j]["lat"], coords[j]["lon"])
            secs = int(km / 30 * 3600)
            row.append(secs)
        matrix.append(row)

    return {
        "source": "haversine_fallback",
        "waypoints": [w.dict() for w in req.waypoints],
        "duration_seconds": matrix,
        "distance_meters": [],
    }


@router.post("/generateTripRoutePlan")
async def generate_trip_route_plan(req: TripRoutePlanRequest):
    """Return ordered route plan for given stops."""
    stops_per_day = max(1, len(req.stops) // max(1, req.duration_days))

    days = []
    for day_idx in range(req.duration_days):
        start = day_idx * stops_per_day
        end = start + stops_per_day if day_idx < req.duration_days - 1 else len(req.stops)
        day_stops = req.stops[start:end]
        days.append({
            "day": day_idx + 1,
            "stops": [s.dict() for s in day_stops],
        })

    return {
        "duration_days": req.duration_days,
        "total_stops": len(req.stops),
        "days": days,
        "routing_mode": "sequential",
    }
