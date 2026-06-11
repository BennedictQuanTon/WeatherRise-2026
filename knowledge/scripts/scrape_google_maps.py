"""
ETL Scraper: Scrape Da Nang tourist attractions & places from Google Maps via Apify.
Placed in knowledge/scripts/ so it is copied into the API container.
Requires APIFY_TOKEN environment variable.

Usage:
    docker exec -e APIFY_TOKEN=apify_api_... -e MAX_PLACES_PER_QUERY=100 -t weatherise-api python3 knowledge/scripts/scrape_google_maps.py
"""
import os
import sys
import json
import time
import requests
import asyncio
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import ingestion pipeline
from knowledge.rag_pipeline.ingestion import async_ingest_places

APIFY_RUN_URL = "https://api.apify.com/v2/acts/compass~crawler-google-places/runs"

# Comprehensive search terms to cover all types of attractions in Da Nang
DEFAULT_QUERIES = [
    "tourist attraction",
    "bãi biển đẹp",
    "chùa nổi tiếng",
    "bảo tàng",
    "khu vui chơi giải trí",
    "địa điểm check-in",
    "công viên đẹp",
    "nhà thờ",
    "cầu nổi tiếng",
    "quán cafe đẹp",
    "nhà hàng nổi tiếng"
]


def map_price_tier(price_level: str) -> str:
    """Map Google Maps price level -> budget/medium/premium."""
    if not price_level:
        return "medium"
    count = len(price_level.strip())
    if count <= 1:
        return "budget"
    elif count <= 2:
        return "medium"
    else:
        return "premium"


def classify_indoor(categories: list) -> bool:
    """Classify place as indoor based on categories."""
    if not categories:
        return False
    cats_lower = [c.lower() for c in categories]
    indoor_keywords = [
        "museum", "church", "pagoda", "temple", "shrine", "indoor", 
        "gallery", "theatre", "cinema", "bảo tàng", "chùa", "nhà thờ", "thánh thất"
    ]
    return any(any(kw in cat for kw in indoor_keywords) for cat in cats_lower)


def map_vibe_tags(categories: list) -> list:
    """Map Google Maps categories -> vibe tags for routing."""
    tags = ["sightseeing"]
    if not categories:
        return tags
    cats_lower = [c.lower() for c in categories]
    for cat in cats_lower:
        if any(kw in cat for kw in ["beach", "ocean", "sea", "bãi biển", "bờ biển"]):
            tags.append("beach")
        if any(kw in cat for kw in ["park", "garden", "nature", "forest", "công viên", "rừng"]):
            tags.append("nature")
        if any(kw in cat for kw in ["museum", "gallery", "bảo tàng", "triển lãm"]):
            tags.append("culture")
        if any(kw in cat for kw in ["church", "temple", "pagoda", "chùa", "nhà thờ", "đền", "miếu"]):
            tags.append("spiritual")
        if any(kw in cat for kw in ["cafe", "coffee", "cà phê", "dessert"]):
            tags.append("cafe")
        if any(kw in cat for kw in ["restaurant", "food", "nhà hàng", "quán ăn"]):
            tags.append("restaurant")
    return list(set(tags))


async def run_scraper(apify_token: str, queries: list, max_places: int = 100):
    """Start Apify run and poll status until complete."""
    headers = {
        "Content-Type": "application/json"
    }
    
    # Configure input payload for apify/google-maps-scraper
    payload = {
        "searchStringsArray": queries,
        "locationQuery": "Da Nang, Vietnam",
        "maxCrawledPlacesPerSearch": max_places,
        "language": "vi",
        "includeReviews": False,
        "maxReviews": 0
    }
    
    print(f"[Apify] Triggering Google Maps Scraper for {len(queries)} search terms...")
    r = requests.post(f"{APIFY_RUN_URL}?token={apify_token}", json=payload, headers=headers)
    if r.status_code != 200 and r.status_code != 201:
        print(f"[Apify Error] Status code: {r.status_code}")
        print(f"[Apify Error] Response body: {r.text}")
    r.raise_for_status()
    run_data = r.json().get("data", {})
    run_id = run_data.get("id")
    dataset_id = run_data.get("defaultDatasetId")
    
    print(f"[Apify] Scraper run started. Run ID: {run_id}. Dataset ID: {dataset_id}")
    print(f"[Apify] Polling status every 15 seconds. Please wait...")
    
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_token}"
    while True:
        status_r = requests.get(status_url)
        status_r.raise_for_status()
        status_data = status_r.json().get("data", {})
        status = status_data.get("status")
        print(f"  -> Current Status: {status}")
        
        if status in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            break
        await asyncio.sleep(15)
        
    if status != "SUCCEEDED":
        raise Exception(f"Apify run finished with status: {status}")
        
    print(f"[Apify] Scraper completed successfully. Fetching raw items...")
    dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}"
    items_r = requests.get(dataset_url)
    items_r.raise_for_status()
    items = items_r.json()
    print(f"[Apify] Downloaded {len(items)} raw listings.")
    return items


async def main():
    apify_token = os.getenv("APIFY_TOKEN")
    if not apify_token:
        print("[Error] APIFY_TOKEN environment variable not set.")
        print("Usage: APIFY_TOKEN=apify_api_XXXXXX python knowledge/scripts/scrape_google_maps.py")
        sys.exit(1)
        
    # Get limit per query (default to 100 listings per query to get complete Da Nang coverage)
    max_places = int(os.getenv("MAX_PLACES_PER_QUERY", "100"))
    
    try:
        items = await run_scraper(apify_token, DEFAULT_QUERIES, max_places)
    except Exception as e:
        print(f"[Error] Scraper execution failed: {e}")
        sys.exit(1)
        
    normalized_places = []
    seen_ids = set()
    
    for item in items:
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
            
        location = item.get("location") or {}
        lat = location.get("lat")
        lng = location.get("lng")
        if not lat or not lng:
            continue
            
        categories = item.get("categories") or []
        sub_cat = categories[0] if categories else "attraction"
        is_indoor = classify_indoor(categories)
        vibe_tags = map_vibe_tags(categories)
        
        # Determine visit duration
        duration = 90 if is_indoor else 60
        if "cafe" in vibe_tags:
            duration = 45
            
        # Map opening hours
        opening_hours = item.get("openingHours") or {}
        
        # Image URL
        image_urls = item.get("imageUrls") or []
        photo_url = image_urls[0] if image_urls else ""
        
        # Weather rules
        weather_rules = {}
        if not is_indoor:
            weather_rules = {"max_wind_kmh": 40, "max_rain_prob_pct": 60}
            
        # Classify main category: cafes and restaurants go to 'restaurant'
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
        
    print(f"[Ingest] Formatted {len(normalized_places)} unique places for ingestion.")
    if not normalized_places:
        print("[Ingest] No locations found. Aborting Ingestion.")
        return
        
    print("[Ingest] Indexing into PostgreSQL and Qdrant collections. Embedding via NIM...")
    # Trigger system's ingestion pipeline (handles vectors and DB rows)
    await async_ingest_places(normalized_places, domain="tourism", source="google_maps_scrape")
    print("[Ingest] ✅ Successfully loaded and embedded Google Maps data!")


if __name__ == "__main__":
    asyncio.run(main())
