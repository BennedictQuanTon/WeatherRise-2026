"""
MCP Route: place.searchPlaces
Phase 3.5: Uses TourismRetriever 3-tier (Qdrant strict → relaxed → Overpass live).
Returns V3 MCPResponseEnvelope.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from mcp.routes.envelope import make_envelope
from knowledge.retrievers.tourism_retriever import TourismRetriever

router = APIRouter()
_retriever = TourismRetriever()


class PlaceSearchRequest(BaseModel):
    location: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    category: Optional[str] = "tourist_attraction"
    limit: int = 20


@router.post("/searchPlaces")
async def search_places(req: PlaceSearchRequest) -> Dict[str, Any]:
    """
    Search tourist attractions using 3-tier KB retrieval:
      Tier 1 → Qdrant strict (score ≥ 0.72)
      Tier 2 → Qdrant relaxed (score ≥ 0.50)
      Tier 3 → Overpass OSM live fetch + async KB ingest
    """
    coordinates = {
        "latitude": req.lat or 16.0544,
        "longitude": req.lon or 108.2022,
    }

    result = await _retriever.get_attractions(
        location=req.location,
        coordinates=coordinates,
        limit=req.limit,
    )

    return make_envelope(
        route="place.searchPlaces",
        context_type="tourist_attractions",
        output={"attractions": result.data, "count": len(result.data)},
        provider=result.source,
        source_type="live" if result.source == "osm_live" else "static",
        freshness="live" if result.source == "osm_live" else "cached",
        input_data={"location": req.location, "lat": req.lat, "lon": req.lon, "limit": req.limit},
        warnings=result.warnings,
        errors=result.errors,
    )


@router.post("/getOpeningHours")
async def get_opening_hours(req: PlaceSearchRequest) -> Dict[str, Any]:
    """Return opening hours map {place_id: {day: hours}} from attraction data."""
    result = await _retriever.get_attractions(
        location=req.location,
        coordinates={"latitude": req.lat or 16.0544, "longitude": req.lon or 108.2022},
        limit=req.limit,
    )
    hours = {
        p["place_id"]: p.get("opening_hours", {"default": "07:00-17:00"})
        for p in result.data
        if "place_id" in p
    }
    return make_envelope(
        route="place.getOpeningHours",
        context_type="opening_hours",
        output={"opening_hours": hours, "count": len(hours)},
        provider=result.source,
        source_type="static",
        freshness="seeded",
        input_data={"location": req.location},
    )


class LiveScrapeRequest(BaseModel):
    query: str
    location: str = "Da Nang, Vietnam"
    limit: int = 5
    apify_token: Optional[str] = None


@router.post("/scrapePlacesLive")
async def scrape_places_live(req: LiveScrapeRequest) -> Dict[str, Any]:
    """
    Trigger real-time Google Maps scraper for a specific query/place.
    Ingests results into PostgreSQL and Qdrant in real-time, then returns them.
    """
    import os
    token = req.apify_token or os.getenv("APIFY_TOKEN")
    if not token:
        return make_envelope(
            route="place.scrapePlacesLive",
            context_type="tourist_attractions",
            output={"attractions": [], "count": 0},
            provider="apify_live",
            errors=["APIFY_TOKEN environment variable not set."],
        )
    
    # We call run_scraper from knowledge.scripts.scrape_google_maps
    from knowledge.scripts.scrape_google_maps import run_scraper, map_price_tier, classify_indoor, map_vibe_tags
    
    try:
        raw_items = await run_scraper(apify_token=token, queries=[req.query], max_places=req.limit)
    except Exception as e:
        return make_envelope(
            route="place.scrapePlacesLive",
            context_type="tourist_attractions",
            output={"attractions": [], "count": 0},
            provider="apify_live",
            errors=[f"Apify execution failed: {str(e)}"],
        )
        
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
            
        loc = item.get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if not lat or not lng:
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
            "city": "Da Nang",
            "country": "Vietnam",
            "latitude": float(lat),
            "longitude": float(lng),
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
        from knowledge.rag_pipeline.ingestion import async_ingest_places
        await async_ingest_places(normalized_places, domain="tourism", source="google_maps_scrape")
        
    return make_envelope(
        route="place.scrapePlacesLive",
        context_type="tourist_attractions",
        output={"attractions": normalized_places, "count": len(normalized_places)},
        provider="apify_live",
        source_type="live",
        freshness="live",
        input_data={"query": req.query, "location": req.location, "limit": req.limit},
    )
