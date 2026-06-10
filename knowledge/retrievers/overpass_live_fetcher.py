"""
Overpass Live Fetcher — Phase 3.5
Fetches tourist attractions from OpenStreetMap Overpass API when Qdrant KB misses.
Serialized (1 request at a time) to respect Overpass rate limits.
Results are normalized to V3 place schema with stable OSM-based place_ids.
"""
import asyncio
import httpx
from typing import List, Dict, Optional

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_SEMAPHORE = asyncio.Semaphore(1)   # Enforce serial access — Overpass is strict

# Tourism-relevant OSM tags to query
TOURISM_TAG_FILTERS = [
    '["tourism"~"attraction|museum|viewpoint|theme_park|artwork|gallery"]',
    '["natural"="beach"]',
    '["leisure"~"park|nature_reserve"]',
    '["amenity"~"place_of_worship"]',
    '["historic"~"monument|ruins|castle|heritage"]',
]

# Which OSM sub-categories are indoor
INDOOR_SUBCATEGORIES = {"museum", "artwork", "gallery", "place_of_worship"}

# Weather risk rules per sub-category
WEATHER_RULES: Dict[str, Dict] = {
    "beach":             {"max_wind_kmh": 35, "max_rain_prob_pct": 50},
    "viewpoint":         {"max_wind_kmh": 40, "max_rain_prob_pct": 60},
    "museum":            {},
    "attraction":        {"max_wind_kmh": 45, "max_rain_prob_pct": 70},
    "theme_park":        {"max_wind_kmh": 40, "max_rain_prob_pct": 60},
    "park":              {"max_wind_kmh": 50, "max_rain_prob_pct": 65},
    "place_of_worship":  {},
    "heritage":          {"max_wind_kmh": 45, "max_rain_prob_pct": 60},
}


class OverpassLiveFetcher:
    """Fetches tourist attractions from OSM Overpass API (Tier 3 fallback)."""

    async def fetch_attractions(
        self,
        lat: float,
        lon: float,
        radius_m: int = 15000,
        limit: int = 25,
    ) -> List[Dict]:
        """
        Live fetch from Overpass API.
        Serialized via semaphore — only 1 concurrent request.
        Returns normalized V3 place dicts ready for Qdrant ingestion.
        """
        tag_lines = "\n".join(
            f"  nwr{tag}(around:{radius_m},{lat},{lon});"
            for tag in TOURISM_TAG_FILTERS
        )
        query = (
            f"[out:json][timeout:20];\n"
            f"(\n{tag_lines}\n);\n"
            f"out center {limit};"
        )

        async with _SEMAPHORE:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.post(
                        OVERPASS_URL,
                        data={"data": query},
                        headers={"User-Agent": "Weatherise/3.0 (hackathon@weatherise.ai)"},
                    )
                    r.raise_for_status()
                    elements = r.json().get("elements", [])
                    return self._normalize(elements)
            except Exception as e:
                print(f"[Overpass] Live fetch failed: {e}")
                return []

    def _normalize(self, elements: List[Dict]) -> List[Dict]:
        """Convert OSM elements → V3 place schema."""
        results = []
        seen: set = set()

        for el in elements:
            tags = el.get("tags", {})

            # Prefer Vietnamese name, fallback to English/default
            name = (
                tags.get("name:vi")
                or tags.get("name")
                or tags.get("name:en")
            )
            if not name:
                continue

            # Get coordinates (node = direct, way/relation = center)
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if not lat or not lon:
                continue

            # Determine sub-category from OSM tags
            sub_cat = "attraction"
            for tag_key in ["tourism", "natural", "leisure", "amenity", "historic"]:
                if tags.get(tag_key):
                    sub_cat = tags[tag_key]
                    break

            # Stable place_id from OSM element ID
            osm_id = el.get("id", 0)
            place_id = f"osm_{osm_id}"
            if place_id in seen:
                continue
            seen.add(place_id)

            # Estimated visit duration
            duration = 90 if sub_cat in {"museum", "theme_park", "gallery"} else 60

            results.append({
                "place_id": place_id,
                "source": "osm_live",
                "name_vi": name,
                "name_en": tags.get("name:en") or name,
                "category": "attraction",
                "sub_category": sub_cat,
                "city": tags.get("addr:city", ""),
                "latitude": float(lat),
                "longitude": float(lon),
                "is_indoor": sub_cat in INDOOR_SUBCATEGORIES,
                "rain_sensitive": sub_cat not in INDOOR_SUBCATEGORIES,
                "bad_weather_rules": WEATHER_RULES.get(sub_cat, {}),
                "vibe_tags": [sub_cat, "sightseeing"],
                "avg_duration_minutes": duration,
                "opening_hours": tags.get("opening_hours", ""),
                "website": tags.get("website", ""),
                "highlights": tags.get("description", ""),
            })

        return results
