"""
Scrape Da Nang tourist attractions from Overpass API (OpenStreetMap).
Free, no API key needed. Run once: python scripts/scrape_osm_attractions.py
"""
import json
import time
import os
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__),
    "../data/mcp_mock/tourism/danang_attractions.json"
)

# Da Nang bounding box: south, west, north, east
BBOX = (15.90, 107.85, 16.25, 108.35)

QUERIES = [
    ('attraction', f'node["tourism"="attraction"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('museum', f'node["tourism"="museum"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('viewpoint', f'node["tourism"="viewpoint"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('beach', f'node["natural"="beach"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('park', f'node["leisure"="park"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('theme_park', f'node["tourism"="theme_park"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
    ('place_of_worship', f'node["amenity"="place_of_worship"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});'),
]

WEATHER_RULES = {
    "beach": {"max_wind_kmh": 35, "max_precipitation_mm": 1.0, "max_rain_prob_pct": 50},
    "viewpoint": {"max_wind_kmh": 40, "max_precipitation_mm": 2.0, "max_rain_prob_pct": 60},
    "park": {"max_wind_kmh": 40, "max_precipitation_mm": 2.0, "max_rain_prob_pct": 60},
    "theme_park": {"max_wind_kmh": 35, "max_precipitation_mm": 1.5, "max_rain_prob_pct": 50},
    "attraction": {"max_wind_kmh": 45, "max_precipitation_mm": 3.0, "max_rain_prob_pct": 70},
    "museum": {},
    "place_of_worship": {"max_wind_kmh": 50, "max_precipitation_mm": 5.0, "max_rain_prob_pct": 80},
}

INDOOR_TYPES = {"museum", "place_of_worship"}
BEST_TIMES = {
    "beach": ["morning", "afternoon"],
    "viewpoint": ["morning", "sunset"],
    "park": ["morning", "afternoon"],
    "attraction": ["morning", "afternoon"],
    "museum": ["morning", "afternoon", "anytime"],
    "place_of_worship": ["morning", "anytime"],
    "theme_park": ["morning", "afternoon"],
}


def slugify(name: str) -> str:
    import re
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    return f"danang_{name[:40]}"


def fetch_osm(query: str) -> list:
    payload = f"[out:json][timeout:25];\n({query});\nout body;"
    try:
        r = requests.post(OVERPASS_URL, data={"data": payload}, timeout=30)
        r.raise_for_status()
        return r.json().get("elements", [])
    except Exception as e:
        print(f"[OSM] Failed: {e}")
        return []


def main():
    all_places = []
    seen_ids = set()

    for cat, query in QUERIES:
        print(f"[OSM] Fetching {cat}...")
        elements = fetch_osm(query)
        print(f"[OSM]   → {len(elements)} results")

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name:vi") or tags.get("name") or tags.get("name:en")
            if not name:
                continue
            lat = el.get("lat")
            lon = el.get("lon")
            if not lat or not lon:
                continue

            pid = slugify(name)
            if pid in seen_ids:
                continue
            seen_ids.add(pid)

            all_places.append({
                "place_id": pid,
                "source": "osm",
                "name_vi": name,
                "name_en": tags.get("name:en") or name,
                "category": "attraction",
                "sub_category": cat,
                "latitude": lat,
                "longitude": lon,
                "city": "Da Nang",
                "country": "Vietnam",
                "is_indoor": cat in INDOOR_TYPES,
                "rain_sensitive": cat not in INDOOR_TYPES,
                "uv_sensitive": cat in {"beach", "viewpoint"},
                "bad_weather_rules": WEATHER_RULES.get(cat, {}),
                "best_visit_times": BEST_TIMES.get(cat, ["morning", "afternoon"]),
                "vibe_tags": [cat, "sightseeing"],
                "avg_duration_minutes": 90 if cat in {"theme_park", "museum"} else 60,
                "safe_alternatives": ["danang_cham_museum", "danang_han_market"],
                "website": tags.get("website", ""),
                "opening_hours": tags.get("opening_hours", ""),
            })

        time.sleep(1.5)  # Respect Overpass rate limit

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_places, f, ensure_ascii=False, indent=2)

    print(f"[OSM] ✅ Saved {len(all_places)} attractions to {OUTPUT_PATH}")
    return all_places


if __name__ == "__main__":
    main()
