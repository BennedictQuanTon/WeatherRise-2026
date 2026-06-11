"""
Trip Context Planner — V3
Builds the trip_plan_context for multi-day itinerary from attractions + restaurants.
Uses distance clustering heuristic + time block allocation.
"""
from typing import List, Dict, Any, Optional
import math


TIME_BLOCK_REGISTRY = {
    "breakfast":          {"label": "Morning Breakfast Window",  "anchor": "08:00", "range": "07:30 - 09:00", "cat": "restaurant", "order": 1},
    "morning_activity":   {"label": "Morning Exploration Block", "anchor": "10:00", "range": "09:00 - 12:00", "cat": "attraction", "order": 2},
    "lunch":              {"label": "Midday Dining Window",      "anchor": "12:30", "range": "12:00 - 13:30", "cat": "restaurant", "order": 3},
    "afternoon_activity": {"label": "Afternoon Prime Block",     "anchor": "15:00", "range": "13:30 - 17:30", "cat": "attraction", "order": 4},
    "dinner":             {"label": "Evening Dining Window",     "anchor": "18:30", "range": "18:00 - 20:00", "cat": "restaurant", "order": 5},
    "evening_relaxation": {"label": "Night Leisure Block",       "anchor": "20:30", "range": "20:00 - 21:30", "cat": "mixed",      "order": 6},
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))



# Semantic vibe groups: places sharing a group can co-cluster on the same day.
# If a place matches multiple groups, the FIRST matching group wins.
VIBE_GROUPS = [
    {"name": "beach_coastal",  "tags": {"beach", "swimming", "surfing", "snorkeling", "ocean_view", "sunrise", "coastal"}},
    {"name": "nature_outdoor", "tags": {"nature", "hiking", "eco", "waterfall", "mountain", "trekking", "viewpoint"}},
    {"name": "culture_history","tags": {"museum", "culture", "history", "heritage", "UNESCO", "ruins", "art", "gallery", "spiritual", "pagoda", "place_of_worship"}},
    {"name": "urban_leisure",  "tags": {"landmark", "night_view", "photo_spot", "bridge", "market", "shopping", "mall", "food_court", "street_food", "local"}},
    {"name": "theme_park",     "tags": {"theme_park", "cable_car", "resort", "amusement", "family"}},
]

def _get_vibe_group(place: Dict) -> str:
    """Return the semantic group name for a place based on its vibe_tags."""
    tags = set(place.get("vibe_tags", []))
    for group in VIBE_GROUPS:
        if tags & group["tags"]:
            return group["name"]
    return "general"


def cluster_by_distance(places: List[Dict], n_days: int) -> List[List[Dict]]:
    """Semantic-aware clustering: group places by vibe compatibility first,
    then by proximity within compatible groups. This prevents semantically
    mismatched places (e.g. museum + beach) from landing in the same day
    purely because they happen to be within 15km of each other."""
    if not places:
        return [[] for _ in range(n_days)]

    # Assign each place its semantic group
    tagged = [(p, _get_vibe_group(p)) for p in places]

    # Build ordered day slots — fill each day greedily, preferring:
    # 1. Same vibe group as the day's seed
    # 2. Proximity within that group
    # 3. Fall through to nearest remaining place if group is exhausted
    remaining = list(tagged)
    clusters: List[List[Dict]] = []
    target_size = max(1, len(places) // n_days)

    for day in range(n_days):
        if not remaining:
            clusters.append([])
            continue

        seed_place, seed_group = remaining.pop(0)
        cluster = [seed_place]

        # First pass: pull same-group places, ordered by proximity
        same_group = [(p, g) for p, g in remaining if g == seed_group]
        same_group.sort(key=lambda pg: haversine_km(
            seed_place.get("latitude", 0), seed_place.get("longitude", 0),
            pg[0].get("latitude", 0), pg[0].get("longitude", 0)
        ))

        for p, g in same_group:
            if len(cluster) >= target_size:
                break
            dist = haversine_km(
                cluster[-1].get("latitude", 0), cluster[-1].get("longitude", 0),
                p.get("latitude", 0), p.get("longitude", 0)
            )
            if dist <= 15:
                cluster.append(p)
                remaining.remove((p, g))

        # Second pass: fill remaining slots with nearest unassigned place
        # (cross-group, only if no more same-group options within 15km)
        while remaining and len(cluster) < target_size:
            anchor = cluster[-1]
            nearest_pg = min(
                remaining,
                key=lambda pg: haversine_km(
                    anchor.get("latitude", 0), anchor.get("longitude", 0),
                    pg[0].get("latitude", 0), pg[0].get("longitude", 0)
                )
            )
            dist = haversine_km(
                anchor.get("latitude", 0), anchor.get("longitude", 0),
                nearest_pg[0].get("latitude", 0), nearest_pg[0].get("longitude", 0)
            )
            if dist > 15:
                break
            cluster.append(nearest_pg[0])
            remaining.remove(nearest_pg)

        clusters.append(cluster)

    return clusters



def build_trip_plan(
    attractions: List[Dict],
    restaurants: List[Dict],
    duration_days: int,
    location: str = "Da Nang",
    weather_forecasts: Optional[Dict] = None,
    indoor_backup_pool: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Build structured trip plan context."""

    # Cluster attractions by proximity
    clusters = cluster_by_distance(attractions, duration_days)

    used_restaurants = set()
    days = []
    carry_over_anchor = None
    for day_idx, day_attractions in enumerate(clusters):
        day_num = day_idx + 1
        stops = []
        stop_order = 1

        # The current spatial anchor updates sequentially as the user moves
        # For multi-day trips, we start Day N+1 from where Day N ended to ensure coherent restaurant search
        if carry_over_anchor and day_idx > 0:
            current_anchor = carry_over_anchor
        else:
            current_anchor = day_attractions[0] if day_attractions else None

        anchor_lat = current_anchor.get("latitude", 16.054) if current_anchor else 16.054
        anchor_lon = current_anchor.get("longitude", 108.202) if current_anchor else 108.202

        # Calculate day centroid for backup filtering
        if day_attractions:
            day_centroid_lat = sum(a.get("latitude", anchor_lat) for a in day_attractions) / len(day_attractions)
            day_centroid_lon = sum(a.get("longitude", anchor_lon) for a in day_attractions) / len(day_attractions)
        else:
            day_centroid_lat, day_centroid_lon = anchor_lat, anchor_lon

        if indoor_backup_pool:
            # Per-day backup pool: only indoor attractions near this cluster (within 15km)
            local_backups = [
                a for a in indoor_backup_pool
                if haversine_km(day_centroid_lat, day_centroid_lon, a.get("latitude", 0), a.get("longitude", 0)) <= 15.0
            ]
            
            # If no local backups found, fallback to the global pool but warn
            if not local_backups:
                local_backups = indoor_backup_pool[:4]
                
            backup_options = [
                {
                    "place_id": a.get("place_id", f"backup_{i}"),
                    "name": a.get("name_vi") or a.get("name", f"Indoor Option {i+1}"),
                    "lat": a.get("latitude", anchor_lat),
                    "lon": a.get("longitude", anchor_lon),
                    "reason": "Indoor backup",
                }
                for i, a in enumerate(local_backups)
            ]
        else:
            backup_options = [
                {"place_id": "danang_cham_museum",  "name": "Cham Museum",  "lat": 16.0668, "lon": 108.2237, "reason": "Indoor backup"},
                {"place_id": "danang_han_market",   "name": "Han Market",   "lat": 16.0749, "lon": 108.2233, "reason": "Indoor backup"},
                {"place_id": "danang_lotte_mart",   "name": "Lotte Mart",   "lat": 16.0316, "lon": 108.2275, "reason": "Indoor backup"},
                {"place_id": "danang_vincom_plaza", "name": "Vincom Plaza", "lat": 16.0716, "lon": 108.2241, "reason": "Indoor backup"},
            ]

        # Assign to time blocks
        attr_iter = iter(day_attractions)

        for block_key, config in sorted(TIME_BLOCK_REGISTRY.items(), key=lambda item: item[1]["order"]):
            expected_cat = config["cat"]
            planned_time = config["anchor"]
            planned_time_window = config["range"]
            stop_order = config["order"]

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
                    "time_block": block_key,
                    "planned_time": planned_time,
                    "planned_time_window": planned_time_window,
                    "forecast_temp": forecast_temp,
                    "weather_condition": weather_cond,
                    "duration_minutes": place.get("avg_duration_minutes", 90),
                    "is_indoor": place.get("is_indoor", False),
                    "category": "attraction",
                    "vibe_tags": place.get("vibe_tags", []),
                })
                current_anchor = place

            elif expected_cat == "restaurant":
                # Dynamically fetch the closest unused restaurant to the current chronological anchor
                best_rest = None
                if current_anchor and restaurants:
                    available = [r for r in restaurants if r.get("place_id") not in used_restaurants]
                    if available:
                        best_rest = min(
                            available,
                            key=lambda r: haversine_km(
                                current_anchor.get("latitude", 0), current_anchor.get("longitude", 0),
                                r.get("latitude", 0), r.get("longitude", 0)
                            )
                        )

                if not best_rest:
                    continue

                # Prevent extreme zig-zagging: if nearest restaurant is more than 8km away,
                # relax the threshold progressively (try 15km) before giving up.
                dist = haversine_km(
                    current_anchor.get("latitude", 0), current_anchor.get("longitude", 0),
                    best_rest.get("latitude", 0), best_rest.get("longitude", 0)
                )

                if dist > 8.0:
                    # Try all remaining restaurants with a 15km soft limit
                    available_relaxed = [r for r in restaurants if r.get("place_id") not in used_restaurants]
                    nearest_relaxed = min(
                        available_relaxed,
                        key=lambda r: haversine_km(
                            current_anchor.get("latitude", 0), current_anchor.get("longitude", 0),
                            r.get("latitude", 0), r.get("longitude", 0)
                        )
                    ) if available_relaxed else None

                    relaxed_dist = haversine_km(
                        current_anchor.get("latitude", 0), current_anchor.get("longitude", 0),
                        nearest_relaxed.get("latitude", 0), nearest_relaxed.get("longitude", 0)
                    ) if nearest_relaxed else 999

                    if relaxed_dist <= 15.0 and nearest_relaxed:
                        best_rest = nearest_relaxed
                        dist = relaxed_dist
                    else:
                        # No real restaurant within 15km — skip this meal slot entirely
                        # (do NOT insert a virtual 'Eating around X' placeholder)
                        print(f"[TripPlanner] No restaurant within 15km of '{current_anchor.get('name_vi')}' ({dist:.1f}km). Skipping meal slot.")
                        continue

                used_restaurants.add(best_rest.get("place_id"))

                stops.append({
                    "order": stop_order,
                    "place_id": best_rest.get("place_id") or best_rest.get("id", f"rest_{day_num}_{stop_order}"),
                    "name": best_rest.get("name_vi") or best_rest.get("name", "Nhà hàng"),
                    "lat": best_rest.get("latitude", 16.054),
                    "lon": best_rest.get("longitude", 108.202),
                    "time_block": block_key,
                    "planned_time": planned_time,
                    "planned_time_window": planned_time_window,
                    "forecast_temp": None,
                    "weather_condition": None,
                    "duration_minutes": 60,
                    "is_indoor": best_rest.get("is_indoor", True),
                    "category": "restaurant",
                    "vibe_tags": best_rest.get("vibe_tags", ["restaurant"]),
                })

            elif expected_cat == "mixed":
                place = next(attr_iter, None)
                if not place:
                    continue

                # Late-Night Eviction Guardrail
                if not place.get("is_indoor", False):
                    # MANDATORY: Substitute inline — never silently shrink the array
                    if backup_options:
                        substitute = backup_options.pop(0)
                        stops.append({
                            "order": stop_order,
                            "place_id": substitute.get("place_id"),
                            "name": substitute.get("name") + " (Night Alternate)",
                            "lat": substitute.get("lat") or (current_anchor.get("latitude", 16.054) if current_anchor else 16.054),
                            "lon": substitute.get("lon") or (current_anchor.get("longitude", 108.202) if current_anchor else 108.202),
                            "time_block": block_key,
                            "planned_time": planned_time,
                            "planned_time_window": planned_time_window,
                            "forecast_temp": None,
                            "weather_condition": None,
                            "duration_minutes": 90,
                            "is_indoor": True,
                            "category": "attraction",
                            "vibe_tags": ["indoor", "backup"],
                        })
                    continue

                stops.append({
                    "order": stop_order,
                    "place_id": place.get("place_id") or place.get("id", f"place_{day_num}_{stop_order}"),
                    "name": place.get("name_vi") or place.get("name", "Unknown"),
                    "lat": place.get("latitude", 16.054),
                    "lon": place.get("longitude", 108.202),
                    "time_block": block_key,
                    "planned_time": planned_time,
                    "planned_time_window": planned_time_window,
                    "forecast_temp": None,
                    "weather_condition": None,
                    "duration_minutes": place.get("avg_duration_minutes", 90),
                    "is_indoor": place.get("is_indoor", False),
                    "category": "attraction",
                    "vibe_tags": place.get("vibe_tags", []),
                })
                current_anchor = place
        # Theme per day based on dominant area
        theme = f"Explore {location}"
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
            "primary_area": location,
            "stops": stops,
            "backup_options": backup_options,
        })
        
        # Save the final anchor of the day to carry over to the next day
        carry_over_anchor = current_anchor

    return {
        "duration_days": duration_days,
        "location": location,
        "planning_mode": "heuristic_v3",
        "days": days,
    }
