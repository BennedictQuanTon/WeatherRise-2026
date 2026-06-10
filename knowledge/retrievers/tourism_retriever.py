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
            return KnowledgeRetrievalResult(
                data=self._results_to_dicts(t1),
                source="qdrant_kb",
                confidence="high",
                search_scores=[r.score for r in t1],
            )

        # ── Tier 2: Qdrant relaxed (score ≥ 0.50, no location filter) ──
        t2 = await self._search_tier2(query=query, limit=limit)
        if len(t2) >= MIN_RESULTS:
            print(f"[TourismRetriever] Tier 2 hit: {len(t2)} results for '{location}' (low confidence)")
            return KnowledgeRetrievalResult(
                data=self._results_to_dicts(t2),
                source="qdrant_kb_low_confidence",
                confidence="medium",
                warnings=[
                    f"No precise KB data for '{location}'. Results may not be location-specific.",
                    "Live fetch recommended for accurate results.",
                ],
                search_scores=[r.score for r in t2],
            )

        # ── Tier 3: Overpass OSM Live Fetch ───────────────────────
        print(f"[TourismRetriever] KB miss for '{location}' → Overpass live fetch (lat={lat}, lon={lon})")
        live_results = await self._overpass.fetch_attractions(
            lat=lat, lon=lon, radius_m=15000, limit=limit
        )

        if live_results:
            # Fire-and-forget: enrich KB for next time
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

        # ── Ultimate fallback: Phase 2 mock data ─────────────────
        print(f"[TourismRetriever] All tiers failed for '{location}' → using mock seed data")
        mock = self._filter_mock_by_location(self._mock_attractions, location)
        return KnowledgeRetrievalResult(
            data=(mock or self._mock_attractions)[:limit],
            source="mock_seed",
            confidence="low" if mock else "none",
            warnings=[
                "Qdrant and Overpass unavailable. Returning static mock data.",
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
        Get restaurants — uses mock/Postgres data (not vector search).
        Optionally filters by near_place_id list for clustering.
        """
        restaurants = self._mock_restaurants

        if near_place_ids:
            nearby = [r for r in restaurants if r.get("near_place_id") in near_place_ids]
            restaurants = nearby if len(nearby) >= 2 else restaurants

        return KnowledgeRetrievalResult(
            data=restaurants[:limit],
            source="mock_seed",
            confidence="high",
            warnings=[] if restaurants else ["No restaurant data available."],
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
