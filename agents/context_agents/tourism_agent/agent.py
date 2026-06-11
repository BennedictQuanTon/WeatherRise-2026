"""
Tourism Context Agent — V3 Full Pipeline
Flow:
  1. Resolve coordinates (known_coords fast-path or Nominatim)
  2. Resolve time range
  3. Get weather forecast (Open-Meteo via MCP)
  4. KB query (TourismRetriever 3-tier: Qdrant → Overpass → mock)
  5. Build ContextGapReport
  6. Call MCP for missing context only
  7. Build trip plan (attractions + interleaved restaurants)
  8. EntityLinker: validate + enrich stops with forecast
  9. Assemble FullyProcessedPayload
"""
from datetime import datetime, timedelta
import asyncio
import time
from typing import List, Dict, Any

from apps.api.app.routes.monitor import emit

from agents.context_agents.base_context_agent import BaseContextAgent
from agents.context_agents.context_gap_report import build_context_gap_report
from agents.context_agents.entity_linker import EntityLinker
from agents.context_agents.context_assembler import assemble_context
from agents.context_agents.tourism_agent.trip_context_planner import build_trip_plan
from knowledge.retrievers.tourism_retriever import TourismRetriever
from apps.api.app.schemas.context_schema import (
    ParserOutput, MCPContext, FullyProcessedPayload,
    KnowledgeContext, IntelligenceRequirements, ContextStatus,
)

OUTDOOR_INTENTS = {"travel_planning", "sightseeing", "beach", "hiking", "outdoor_activity"}
BEACH_INTENTS = {"beach", "swimming", "surfing"}


class TourismContextAgent(BaseContextAgent):
    domain = "tourism"

    def __init__(self):
        super().__init__()
        self._retriever = TourismRetriever()
        self._linker = EntityLinker()

    def get_required_context(self, parsed: ParserOutput) -> List[str]:
        intent = parsed.intent.lower()
        ctx = ["weather_forecast", "tourist_attractions", "weather_risk_rules"]
        if parsed.intent_subtype == "multi_day_trip_planning":
            ctx += [
                "restaurants", "opening_hours",
                "indoor_outdoor_classification", "trip_route_plan", "backup_plan_options",
            ]
        elif any(k in intent for k in OUTDOOR_INTENTS):
            ctx += ["opening_hours", "backup_plan_options"]
        if any(k in intent for k in BEACH_INTENTS):
            ctx += ["storm_risk", "uv_index"]
        return list(dict.fromkeys(ctx))

    def get_weather_variables(self, intent: str) -> List[str]:
        base = ["rain_probability", "temperature", "wind_speed", "humidity"]
        if "beach" in intent.lower():
            base += ["uv_index", "storm_risk"]
        return base

    async def process(self, parsed: ParserOutput) -> FullyProcessedPayload:
        """Full V3 pipeline with KB-Miss → Live Fetch → Context Assembly."""
        location = parsed.location or "Da Nang"
        mcp_ctx = MCPContext()
        mcp_routes_called = []

        # ── 1. Phase I: Resolve Coordinates and Time Range ────────────────
        t_phase1 = time.time()
        tasks_phase1 = [
            self.call_mcp("location.resolveCoordinates", {"location": location})
        ]
        has_time_raw = bool(parsed.time_range and parsed.time_range.raw_text)
        if has_time_raw:
            tasks_phase1.append(self.call_mcp("time.resolveTimeRange", {
                "raw_text": parsed.time_range.raw_text,
                "timezone": getattr(parsed.time_range, "timezone", "Asia/Ho_Chi_Minh"),
            }))
            
        results_phase1 = await asyncio.gather(*tasks_phase1)
        
        coord_result = results_phase1[0]
        mcp_routes_called.append("location.resolveCoordinates")
        
        coords = coord_result.get("output", coord_result)  # handle both envelope and raw
        lat = coords.get("latitude") or 16.0544
        lon = coords.get("longitude") or 108.2022
        mcp_ctx.coordinates = {"latitude": lat, "longitude": lon}
        parsed.geographical_location.coordinates = mcp_ctx.coordinates

        if has_time_raw:
            time_result = results_phase1[1]
            mcp_routes_called.append("time.resolveTimeRange")
            tr = time_result.get("output", time_result)
            if tr.get("start"):
                parsed.time_range.start = tr["start"]
                parsed.time_range.end = tr.get("end")
                mcp_ctx.time_range_resolved = tr

        # Fallback dates
        if not (parsed.time_range and parsed.time_range.start):
            now = datetime.now()
            n_days = (
                (parsed.trip_request.duration_days or 3)
                if parsed.trip_request else 3
            )
            if parsed.time_range:
                parsed.time_range.start = now.strftime("%Y-%m-%d")
                parsed.time_range.end = (now + timedelta(days=n_days)).strftime("%Y-%m-%d")

        # Ensure end date covers duration if it's a trip
        if parsed.time_range and parsed.time_range.start and parsed.trip_request and parsed.trip_request.duration_days:
            try:
                start_dt = datetime.strptime(parsed.time_range.start, "%Y-%m-%d")
                duration = parsed.trip_request.duration_days
                current_end = parsed.time_range.end
                if current_end:
                    end_dt = datetime.strptime(current_end, "%Y-%m-%d")
                    if (end_dt - start_dt).days < duration:
                        parsed.time_range.end = (start_dt + timedelta(days=duration)).strftime("%Y-%m-%d")
                else:
                    parsed.time_range.end = (start_dt + timedelta(days=duration)).strftime("%Y-%m-%d")
            except Exception:
                pass

        ms_phase1 = int((time.time() - t_phase1) * 1000)
        emit("step", "TourismAgent", "Phase I: Coordinates & Time resolved", duration_ms=ms_phase1)

        # ── 3. Phase II: Weather Forecast and KB Queries ──────────────────
        t_phase2 = time.time()
        forecast_task = self.call_mcp("weather.getForecast", {
            "latitude": lat,
            "longitude": lon,
            "start_date": getattr(parsed.time_range, "start", None),
            "end_date": getattr(parsed.time_range, "end", None),
        })
        attr_task = self._retriever.get_attractions(
            location=location,
            coordinates=mcp_ctx.coordinates,
            limit=20,
        )
        rest_task = self._retriever.get_restaurants(
            location=location,
            coordinates=mcp_ctx.coordinates,
            limit=15,
        )

        forecast_result, kb_attractions, kb_restaurants = await asyncio.gather(
            forecast_task, attr_task, rest_task
        )

        ms_phase2 = int((time.time() - t_phase2) * 1000)
        emit("step", "TourismAgent", "Phase II: KB & Forecast fetch", duration_ms=ms_phase2, data={
            "kb_attractions": len(kb_attractions.data or []),
            "kb_restaurants": len(kb_restaurants.data or [])
        })

        # ── Supplement attractions via MCP place.searchPlaces ────────────
        t_mcp = time.time()
        kb_attr_is_sparse = (
            not kb_attractions.data
            or kb_attractions.source in ("mock_seed", "mock")
            or len(kb_attractions.data) < 5
        )
        if kb_attr_is_sparse:
            print(f"[TourismAgent] KB attractions sparse ({kb_attractions.source}, {len(kb_attractions.data or [])} results). Calling MCP place.searchPlaces...")
            try:
                mcp_places_result = await self.call_mcp("place.searchPlaces", {
                    "location": location,
                    "lat": lat,
                    "lon": lon,
                    "limit": 20,
                })
                mcp_attractions = (
                    mcp_places_result.get("output", {}).get("attractions", [])
                    if isinstance(mcp_places_result, dict) else []
                )
                if mcp_attractions:
                    existing_ids = {a.get("place_id") for a in (kb_attractions.data or [])}
                    new_attrs = [a for a in mcp_attractions if a.get("place_id") not in existing_ids]
                    kb_attractions.data = new_attrs + (kb_attractions.data or [])
                    kb_attractions.source = mcp_places_result.get("provider", "mcp_place_search")
                    print(f"[TourismAgent] MCP added {len(new_attrs)} new attractions. Total: {len(kb_attractions.data)}")
                    mcp_routes_called.append("place.searchPlaces")
            except Exception as e:
                print(f"[TourismAgent] MCP place.searchPlaces failed: {e}. Continuing with KB data.")

        # ── Supplement restaurants: per-cluster centroid search ──────────────
        # The critical insight: attractions may be fetched from remote coordinates
        # (e.g. Overpass for Hoi An, My Son, Ba Na Hills) that are far from the
        # city-level lat/lon used for the initial restaurant KB query.
        # We pre-cluster the attractions (same algorithm as build_trip_plan),
        # compute each cluster's centroid, and call place.searchRestaurants once
        # per cluster. This ensures restaurants are always sourced from WHERE the
        # user will actually be, not just the city center.
        kb_rest_is_sparse = (
            not kb_restaurants.data
            or kb_restaurants.source in ("mock_seed", "mock")
            or len(kb_restaurants.data) < 8
        )
        if kb_rest_is_sparse and kb_attractions.data:
            from agents.context_agents.tourism_agent.trip_context_planner import cluster_by_distance
            is_trip = parsed.intent_subtype == "multi_day_trip_planning"
            duration_days = (
                (parsed.trip_request.duration_days or 3)
                if parsed.trip_request else 3
            )
            n_clusters = duration_days if is_trip else 1
            clusters = cluster_by_distance(kb_attractions.data, n_clusters)

            # Compute centroid of each cluster
            cluster_centroids = []
            for cluster in clusters:
                if not cluster:
                    continue
                c_lat = sum(a.get("latitude", lat) for a in cluster) / len(cluster)
                c_lon = sum(a.get("longitude", lon) for a in cluster) / len(cluster)
                cluster_centroids.append((c_lat, c_lon))

            print(f"[TourismAgent] Calling place.searchRestaurants for {len(cluster_centroids)} cluster centroids...")
            existing_ids = {r.get("place_id") for r in (kb_restaurants.data or [])}
            all_new_rests = []

            for c_lat, c_lon in cluster_centroids:
                try:
                    mcp_rest_result = await self.call_mcp("place.searchRestaurants", {
                        "location": location,
                        "lat": c_lat,
                        "lon": c_lon,
                        "radius_km": 10.0,
                        "limit": 15,
                    })
                    mcp_restaurants = (
                        mcp_rest_result.get("output", {}).get("restaurants", [])
                        if isinstance(mcp_rest_result, dict) else []
                    )
                    for r in mcp_restaurants:
                        pid = r.get("place_id")
                        if pid and pid not in existing_ids:
                            all_new_rests.append(r)
                            existing_ids.add(pid)
                except Exception as e:
                    print(f"[TourismAgent] MCP place.searchRestaurants failed for centroid ({c_lat:.4f},{c_lon:.4f}): {e}")

            if all_new_rests:
                kb_restaurants.data = all_new_rests + (kb_restaurants.data or [])
                print(f"[TourismAgent] Per-cluster MCP added {len(all_new_rests)} restaurants. Total: {len(kb_restaurants.data)}")
                mcp_routes_called.append("place.searchRestaurants")
            else:
                print(f"[TourismAgent] Per-cluster MCP returned 0 new restaurants. Existing pool: {len(kb_restaurants.data or [])}.")
        
        if kb_attr_is_sparse or (kb_rest_is_sparse and kb_attractions.data):
            ms_mcp = int((time.time() - t_mcp) * 1000)
            emit("step", "TourismAgent", "Phase III: MCP Fallbacks", duration_ms=ms_mcp, data={
                "mcp_routes": [r for r in mcp_routes_called if "place" in r]
            })

        mcp_routes_called.append("weather.getForecast")
        if forecast_result:
            mcp_ctx.weather_forecast = forecast_result

        # ── 4b. Extract & Prepend User-Requested Specific Places ─
        preferred_places = []
        if parsed.trip_request and parsed.trip_request.preferences:
            from knowledge.vector_store.client import VectorStoreClient
            vs = VectorStoreClient()
            for pref in parsed.trip_request.preferences:
                if len(pref) > 4 and pref.lower() not in {"seafood", "nature", "beach", "photo_spot", "family_friendly", "tránh mưa", "rain_sensitive", "indoor", "general", "balanced", "relaxed"}:
                    print(f"[TourismContextAgent] Querying Qdrant specifically for preferred place: '{pref}'")
                    try:
                        results = await vs.search(
                            collection="tourism_knowledge",
                            query_text=pref,
                            score_threshold=0.42,
                            limit=3
                        )
                        for r in results:
                            place_dict = {
                                **r.payload,
                                "place_id": r.place_id,
                                "search_score": r.score
                            }
                            preferred_places.append(place_dict)
                    except Exception as e:
                        print(f"[TourismContextAgent] Error searching preferred place '{pref}': {e}")
                        
        if preferred_places:
            existing_attr_ids = {p.get("place_id") or p.get("id") for p in kb_attractions.data} if kb_attractions.data else set()
            existing_rest_ids = {p.get("place_id") or p.get("id") for p in kb_restaurants.data} if kb_restaurants.data else set()
            
            added_attrs = []
            added_rests = []
            
            for p in preferred_places:
                pid = p.get("place_id") or p.get("id")
                if p.get("category") == "restaurant":
                    if pid not in existing_rest_ids:
                        added_rests.append(p)
                        existing_rest_ids.add(pid)
                else:
                    if pid not in existing_attr_ids:
                        added_attrs.append(p)
                        existing_attr_ids.add(pid)
            
            if added_attrs and kb_attractions.data is not None:
                kb_attractions.data = added_attrs + kb_attractions.data
                print(f"[TourismContextAgent] Added {len(added_attrs)} preferred attractions: {[x.get('name_vi') for x in added_attrs]}")
            if added_rests and kb_restaurants.data is not None:
                kb_restaurants.data = added_rests + kb_restaurants.data
                print(f"[TourismContextAgent] Added {len(added_rests)} preferred restaurants: {[x.get('name_vi') for x in added_rests]}")

        # ── 5. Context Gap Report ────────────────────────────────
        involved_context = self.get_required_context(parsed)
        kb_data = {
            "tourist_attractions": kb_attractions.data if not kb_attractions.is_empty else None,
            "weather_forecast": bool(mcp_ctx.weather_forecast),
            "restaurants": kb_restaurants.data if not kb_restaurants.is_empty else None,
        }
        gap_report = build_context_gap_report(
            required=involved_context,
            kb_results=kb_data,
            domain=self.domain,
            location=location,
        )

        # ── 6. Fill MCP context with KB results ──────────────────
        mcp_ctx.places = kb_attractions.data
        mcp_ctx.restaurants = kb_restaurants.data

        # ── 7. Build Trip Plan (if multi-day) ────────────────────
        t_plan = time.time()
        is_trip = parsed.intent_subtype == "multi_day_trip_planning"
        if is_trip and kb_attractions.data:
            duration_days = (
                (parsed.trip_request.duration_days or 3)
                if parsed.trip_request else 3
            )
            daily_forecasts = (
                forecast_result.get("output", {}).get("daily_forecasts", [])
                if isinstance(forecast_result, dict) else []
            )
            # Build a lookup for indoor attractions to use as map-accurate backup options
            indoor_attrs = [
                a for a in (kb_attractions.data or [])
                if a.get("is_indoor", False)
            ][:6]
            trip_plan = build_trip_plan(
                attractions=kb_attractions.data,
                restaurants=kb_restaurants.data,
                duration_days=duration_days,
                location=location,
                weather_forecasts=None,  # Handled by ContextAssembler
                indoor_backup_pool=indoor_attrs,
            )
            mcp_ctx.trip_plan_context = trip_plan

        if is_trip:
            ms_plan = int((time.time() - t_plan) * 1000)
            emit("step", "TourismAgent", "Phase IV: Trip Planning", duration_ms=ms_plan)

        # ── 8. Assemble + Entity Link + Forecast Enrich ──────────
        return assemble_context(
            parsed=parsed,
            mcp_ctx=mcp_ctx,
            gap_report=gap_report,
            kb_context=KnowledgeContext(),
            mcp_routes_called=mcp_routes_called,
        )
