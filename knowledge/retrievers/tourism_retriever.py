"""
TourismRetriever — V3 Three-Tier Retrieval
Implements the KB-Miss → Live Fetch → Async Ingest pattern:

  Tier 1: Qdrant strict search (score ≥ 0.72) — high confidence KB hit
  Tier 2: Qdrant relaxed search (score ≥ 0.50) — low confidence KB hit
  Tier 3: Overpass OSM live fetch → fire-and-forget ingest → return live data

Also provides get_restaurants() that reads from mock/Postgres (no vector search).
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from knowledge.retrievers.base_retriever import (
    BaseRetriever, KnowledgeRetrievalResult, MIN_RESULTS
)
from knowledge.retrievers.overpass_live_fetcher import OverpassLiveFetcher
from knowledge.rag_pipeline.ingestion import async_ingest_places

# Mock data paths (Phase 2 data — used when Qdrant has no data yet)
_MOCK_DIR = Path(__file__).parent.parent.parent / "data" / "mcp_mock" / "tourism"


def _load_mock_json(filename: str) -> List[Dict]:
    path = _MOCK_DIR / filename
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


class TourismRetriever(BaseRetriever):
    """
    3-tier retriever for tourist attractions.
    Tier 1 → Tier 2 → Tier 3 (Overpass live) with async KB enrichment.
    Falls back gracefully to mock data if Qdrant is unavailable.
    """

    def __init__(self):
        super().__init__(collection_name="tourism_knowledge")
        self._overpass = OverpassLiveFetcher()
        # Preload mock as absolute last resort (no network needed)
        self._mock_attractions = _load_mock_json("danang_attractions.json")
        self._mock_restaurants = _load_mock_json("danang_restaurants.json")

    async def get_attractions(
        self,
        location: str,
        coordinates: Dict[str, float],
        limit: int = 20,
    ) -> KnowledgeRetrievalResult:
        """
        Get tourist attractions for location via 3-tier retrieval.
        Always returns data — never empty if Overpass is reachable.
        """
        lat = coordinates.get("latitude", 16.0544)
        lon = coordinates.get("longitude", 108.2022)
        query = f"tourist attractions things to do in {location}"

        # ── Tier 1: Qdrant strict (score ≥ 0.72) ─────────────────
        t1 = await self._search_tier1(
            query=query,
            filters={"city": location},
            limit=limit,
        )
        if len(t1) >= MIN_RESULTS:
            print(f"[TourismRetriever] Tier 1 hit: {len(t1)} results for '{location}'")
            # Sort: google_maps_scrape source first
            t1_sorted = sorted(t1, key=lambda r: 0 if r.payload.get("source") == "google_maps_scrape" else 1)
            return KnowledgeRetrievalResult(
                data=self._results_to_dicts(t1_sorted),
                source="qdrant_kb",
                confidence="high",
                search_scores=[r.score for r in t1_sorted],
            )

        # ── Tier 2: Qdrant relaxed (score ≥ 0.50, no location filter) ──
        t2 = await self._search_tier2(query=query, limit=limit)
        if len(t2) >= MIN_RESULTS:
            print(f"[TourismRetriever] Tier 2 hit: {len(t2)} results for '{location}' (low confidence)")
            # Sort: google_maps_scrape source first
            t2_sorted = sorted(t2, key=lambda r: 0 if r.payload.get("source") == "google_maps_scrape" else 1)
            return KnowledgeRetrievalResult(
                data=self._results_to_dicts(t2_sorted),
                source="qdrant_kb_low_confidence",
                confidence="medium",
                warnings=[
                    f"No precise KB data for '{location}'. Results may not be location-specific.",
                    "Live fetch recommended for accurate results.",
                ],
                search_scores=[r.score for r in t2_sorted],
            )

        # ── Tier 3: Live Fetch (Apify Google Maps first, then OSM Overpass) ────
        import os
        apify_token = os.getenv("APIFY_TOKEN")
        if apify_token:
            print(f"[TourismRetriever] KB miss for '{location}' → Apify Google Maps live fetch (query='tourist attraction in {location}')")
            try:
                from knowledge.scripts.scrape_google_maps import run_scraper, map_price_tier, classify_indoor, map_vibe_tags
                raw_items = await run_scraper(apify_token=apify_token, queries=[f"tourist attraction in {location}"], max_places=5)
                
                normalized_places = []
                seen_ids = set()
                for item in raw_items:
                    place_id = item.get("placeId")
                    if not place_id:
                        continue
                    pid = f"gmaps_{place_id}"
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    
                    name = item.get("title") or item.get("displayName")
                    if not name:
                        continue
                        
                    loc_val = item.get("location") or {}
                    lat_val = loc_val.get("lat")
                    lng_val = loc_val.get("lng")
                    if not lat_val or not lng_val:
                        continue
                        
                    categories = item.get("categories") or []
                    sub_cat = categories[0] if categories else "attraction"
                    is_indoor = classify_indoor(categories)
                    vibe_tags = map_vibe_tags(categories)
                    
                    duration = 90 if is_indoor else 60
                    if "cafe" in vibe_tags:
                        duration = 45
                        
                    opening_hours = item.get("openingHours") or {}
                    image_urls = item.get("imageUrls") or []
                    photo_url = image_urls[0] if image_urls else ""
                    
                    weather_rules = {}
                    if not is_indoor:
                        weather_rules = {"max_wind_kmh": 40, "max_rain_prob_pct": 60}
                        
                    main_category = "attraction"
                    if "cafe" in vibe_tags or "restaurant" in vibe_tags:
                        main_category = "restaurant"

                    normalized_places.append({
                        "place_id": pid,
                        "source": "google_maps_scrape",
                        "name_vi": name,
                        "name_en": name,
                        "category": main_category,
                        "sub_category": sub_cat,
                        "address": item.get("address", ""),
                        "city": location,
                        "country": "Vietnam",
                        "latitude": float(lat_val),
                        "longitude": float(lng_val),
                        "avg_rating": float(item.get("rating") or 0.0),
                        "total_reviews": int(item.get("reviewCount") or 0),
                        "price_tier": map_price_tier(item.get("priceLevel")),
                        "avg_duration_minutes": duration,
                        "is_indoor": is_indoor,
                        "rain_sensitive": not is_indoor,
                        "uv_sensitive": "beach" in vibe_tags or "nature" in vibe_tags,
                        "bad_weather_rules": weather_rules,
                        "vibe_tags": vibe_tags,
                        "is_opening": True,
                        "photo_url": photo_url,
                        "phone": item.get("phone", ""),
                        "website": item.get("website", ""),
                        "opening_hours": opening_hours,
                    })
                
                if normalized_places:
                    print(f"[TourismRetriever] Apify live fetch succeeded, ingesting {len(normalized_places)} places.")
                    await async_ingest_places(normalized_places, domain="tourism", source="google_maps_scrape")
                    return KnowledgeRetrievalResult(
                        data=normalized_places,
                        source="google_maps_scrape",
                        confidence="high",
                        warnings=[
                            "Data fetched live from Google Maps via Apify.",
                            "Results have been indexed into the Knowledge Base.",
                        ],
                    )
            except Exception as e:
                print(f"[TourismRetriever] Apify live fetch failed: {e}. Falling back to Overpass...")

        print(f"[TourismRetriever] KB miss for '{location}' → Overpass live fetch (lat={lat}, lon={lon})")
        live_results = await self._overpass.fetch_attractions(
            lat=lat, lon=lon, radius_m=15000, limit=limit
        )

        if live_results:
            asyncio.create_task(
                async_ingest_places(live_results, domain="tourism", source="osm_live")
            )
            return KnowledgeRetrievalResult(
                data=live_results,
                source="osm_live",
                confidence="high",
                warnings=[
                    "Data fetched live from OpenStreetMap Overpass API.",
                    "Results are being asynchronously indexed into the Knowledge Base.",
                ],
            )

        print(f"[TourismRetriever] All live tiers failed for '{location}' → using mock seed data")
        mock = self._filter_mock_by_location(self._mock_attractions, location)
        return KnowledgeRetrievalResult(
            data=(mock or self._mock_attractions)[:limit],
            source="mock_seed",
            confidence="low" if mock else "none",
            warnings=[
                "Qdrant and live services unavailable. Returning static mock data.",
                "Results may not match the requested location precisely.",
            ],
        )

    async def get_restaurants(
        self,
        location: str,
        coordinates: Dict[str, float],
        near_place_ids: Optional[List[str]] = None,
        limit: int = 15,
    ) -> KnowledgeRetrievalResult:
        """
        Get restaurants — uses PostgreSQL if available, otherwise falls back to mock.
        Prioritizes google_maps_scrape over foody_csv, and sorts by proximity.
        """
        import os
        postgres_url = os.getenv("POSTGRES_URL")
        
        lat = coordinates.get("latitude", 16.0544)
        lon = coordinates.get("longitude", 108.2022)
        radius_m = 10000.0  # 10 km search radius
        
        if postgres_url:
            try:
                import asyncpg
                conn = await asyncio.wait_for(
                    asyncpg.connect(postgres_url),
                    timeout=5.0
                )
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
                rows = await conn.fetch(query, lon, lat, radius_m, limit)
                await conn.close()
                
                if rows:
                    res_list = [
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
                            "source": r["source"],
                            "distance_m": round(float(r["dist_m"]), 0),
                        }
                        for r in rows
                    ]
                    return KnowledgeRetrievalResult(
                        data=res_list,
                        source="postgresql_db",
                        confidence="high",
                    )
            except Exception as e:
                print(f"[TourismRetriever] PostgreSQL query failed: {e}. Falling back to mock...")

        restaurants = self._mock_restaurants
        if near_place_ids:
            nearby = [r for r in restaurants if r.get("near_place_id") in near_place_ids]
            restaurants = nearby if len(nearby) >= 2 else restaurants

        return KnowledgeRetrievalResult(
            data=restaurants[:limit],
            source="mock_seed",
            confidence="high",
            warnings=["Using fallback mock restaurant data due to DB unavailable."] if postgres_url else [],
        )

    async def get_weather_rules(self, domain: str = "tourism") -> List[Dict]:
        """Retrieve weather risk rules from KB (Qdrant or defaults)."""
        results = await self._search_tier1(
            query=f"weather risk rules {domain} safety thresholds",
            filters={"domain": domain},
            limit=10,
        )
        if results:
            return self._results_to_dicts(results)
        # Hardcoded defaults if KB has no weather rules yet
        return [
            {"domain": "tourism", "rule": "avoid_beach_high_rain", "max_rain_prob_pct": 50},
            {"domain": "tourism", "rule": "avoid_outdoor_heavy_wind", "max_wind_kmh": 40},
        ]

    def _filter_mock_by_location(self, places: List[Dict], location: str) -> List[Dict]:
        """Filter mock places by city name match."""
        loc_lower = location.lower()
        return [
            p for p in places
            if loc_lower in p.get("city", "").lower()
            or p.get("city", "").lower() in loc_lower
        ]
