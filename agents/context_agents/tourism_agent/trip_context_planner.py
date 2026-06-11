"""
Trip Context Planner — V3
Builds the trip_plan_context for multi-day itinerary from attractions + restaurants.
Uses distance clustering heuristic + time block allocation.
"""
from typing import List, Dict, Any, Optional
import math


TIME_BLOCKS = ["morning", "lunch", "afternoon", "dinner", "evening"]

TIME_BLOCK_HOURS = {
    "morning": "08:00",
    "lunch": "12:00",
    "afternoon": "14:30",
    "dinner": "18:30",
    "evening": "20:00",
}

BLOCK_CATEGORY = {
    "morning": "attraction",
    "lunch": "restaurant",
    "afternoon": "attraction",
    "dinner": "restaurant",
    "evening": "attraction",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cluster_by_distance(places: List[Dict], n_days: int) -> List[List[Dict]]:
    """Greedy clustering: group nearby places into daily clusters."""
    if not places:
        return [[] for _ in range(n_days)]

    remaining = list(places)
    clusters = []

    for day in range(n_days):
        if not remaining:
            clusters.append([])
            continue
        # Start cluster with first remaining place
        cluster = [remaining.pop(0)]
        target_size = max(1, len(places) // n_days)

        while remaining and len(cluster) < target_size:
            anchor = cluster[-1]
            # Find nearest unassigned place
            nearest = min(
                remaining,
                key=lambda p: haversine_km(
                    anchor.get("latitude", 0), anchor.get("longitude", 0),
                    p.get("latitude", 0), p.get("longitude", 0)
                )
            )
            dist = haversine_km(
                anchor.get("latitude", 0), anchor.get("longitude", 0),
                nearest.get("latitude", 0), nearest.get("longitude", 0)
            )
            if dist > 15:  # Don't group places more than 15km apart
                break
            cluster.append(nearest)
            remaining.remove(nearest)

        clusters.append(cluster)

    return clusters


def build_trip_plan(
    attractions: List[Dict],
    restaurants: List[Dict],
    duration_days: int,
    location: str = "Da Nang",
    weather_forecasts: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build structured trip plan context."""

    # Cluster attractions by proximity
    clusters = cluster_by_distance(attractions, duration_days)

    days = []
    for day_idx, day_attractions in enumerate(clusters):
        day_num = day_idx + 1
        stops = []
        stop_order = 1

        # Find nearby restaurants for this day's attractions
        day_anchor = day_attractions[0] if day_attractions else None
        day_restaurants = []
        if day_anchor and restaurants:
            day_restaurants = sorted(
                restaurants,
                key=lambda r: (
                    0 if "search_score" in r or r.get("source") == "google_maps_scrape" else 1,
                    haversine_km(
                        day_anchor.get("latitude", 0), day_anchor.get("longitude", 0),
                        r.get("latitude", 0), r.get("longitude", 0)
                    )
                )
            )[:4]  # top 4 nearest/preferred restaurants

        # Assign to time blocks
        attr_iter = iter(day_attractions)
        rest_iter = iter(day_restaurants)

        for block in TIME_BLOCKS:
            expected_cat = BLOCK_CATEGORY[block]
            planned_time = TIME_BLOCK_HOURS[block]

            if expected_cat == "attraction":
                place = next(attr_iter, None)
                if not place:
                    continue
                # Check weather suitability
                forecast_temp = None
                weather_cond = "Unknown"
                if weather_forecasts:
                    hour_data = weather_forecasts.get(planned_time[:2], {})
                    forecast_temp = hour_data.get("temp")
                    weather_cond = hour_data.get("condition", "Unknown")

                stops.append({
                    "order": stop_order,
                    "place_id": place.get("place_id") or place.get("id", f"place_{day_num}_{stop_order}"),
                    "name": place.get("name_vi") or place.get("name", "Unknown"),
                    "lat": place.get("latitude", 16.054),
                    "lon": place.get("longitude", 108.202),
                    "time_block": block,
                    "planned_time": planned_time,
                    "forecast_temp": forecast_temp,
                    "weather_condition": weather_cond,
                    "duration_minutes": place.get("avg_duration_minutes", 90),
                    "is_indoor": place.get("is_indoor", False),
                    "category": "attraction",
                    "vibe_tags": place.get("vibe_tags", []),
                })
                stop_order += 1

            elif expected_cat == "restaurant":
                rest = next(rest_iter, None)
                if not rest:
                    continue
                stops.append({
                    "order": stop_order,
                    "place_id": rest.get("place_id") or rest.get("id", f"rest_{day_num}_{stop_order}"),
                    "name": rest.get("name_vi") or rest.get("name", "Nhà hàng"),
                    "lat": rest.get("latitude", 16.054),
                    "lon": rest.get("longitude", 108.202),
                    "time_block": block,
                    "planned_time": planned_time,
                    "forecast_temp": None,
                    "weather_condition": None,
                    "duration_minutes": 60,
                    "is_indoor": rest.get("is_indoor", True),
                    "category": "restaurant",
                    "vibe_tags": rest.get("vibe_tags", ["restaurant"]),
                })
                stop_order += 1

        # Backup options: indoor alternatives
        backup_options = [
            {"place_id": "danang_cham_museum", "name": "Cham Museum", "reason": "Indoor backup"},
            {"place_id": "danang_han_market", "name": "Han Market", "reason": "Indoor backup"},
        ]

        # Theme per day based on dominant area
        theme = "Explore Da Nang"
        if day_attractions:
            tags = []
            for a in day_attractions:
                tags.extend(a.get("vibe_tags", []))
            if "beach" in tags:
                theme = "Beach & Seafood"
            elif "museum" in tags or "culture" in tags:
                theme = "Culture & History"
            elif "viewpoint" in tags or "mountain" in tags:
                theme = "Sightseeing & Nature"

        days.append({
            "day": day_num,
            "theme": theme,
            "primary_area": "Da Nang",
            "stops": stops,
            "backup_options": backup_options,
        })

    return {
        "duration_days": duration_days,
        "location": location,
        "planning_mode": "heuristic_v3",
        "days": days,
    }
