#!/usr/bin/env python3
"""
Qdrant KB Seeder — V3
Seeds the tourism_knowledge collection with danang_attractions.json mock data.
Run this ONCE to populate Qdrant so TourismRetriever Tier 1 works immediately.

Usage:
    python3 knowledge/scripts/seed_qdrant.py
    python3 knowledge/scripts/seed_qdrant.py --collection tourism_knowledge --force
"""
import asyncio
import argparse
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from knowledge.rag_pipeline.ingestion import async_ingest_places
from knowledge.vector_store.client import VectorStoreClient
from knowledge.vector_store.collections import COLLECTIONS

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "mcp_mock" / "tourism"


async def seed_tourism(force: bool = False):
    vs = VectorStoreClient()

    # Check if already seeded
    if not force:
        exists = await vs.collection_exists("tourism_knowledge")
        if exists:
            # Quick check: does it have any vectors?
            import httpx
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{vs.qdrant_url}/collections/tourism_knowledge")
                    info = r.json()
                    count = info.get("result", {}).get("points_count", 0)
                    if count > 0:
                        print(f"[Seed] tourism_knowledge already has {count} vectors. Use --force to re-seed.")
                        return
            except Exception:
                pass

    # Load attractions
    attractions_path = DATA_DIR / "danang_attractions.json"
    if not attractions_path.exists():
        print(f"[Seed] ERROR: {attractions_path} not found")
        return

    with open(attractions_path, encoding="utf-8") as f:
        attractions = json.load(f)

    print(f"[Seed] Seeding {len(attractions)} Da Nang attractions into tourism_knowledge...")
    await async_ingest_places(attractions, domain="tourism", source="seed_danang")
    print(f"[Seed] ✅ Done!")


async def main():
    parser = argparse.ArgumentParser(description="Seed Qdrant KB with tourism data")
    parser.add_argument("--force", action="store_true", help="Re-seed even if collection exists")
    parser.add_argument("--collection", default="tourism_knowledge", help="Collection name")
    args = parser.parse_args()

    print("[Seed] Starting Qdrant KB seeding...")
    print(f"[Seed] Qdrant URL: {os.getenv('QDRANT_URL', 'http://localhost:6333')}")
    print(f"[Seed] NIM Embed: {os.getenv('NIM_EMBED_BASE_URL', 'http://localhost:8002/v1')}")
    print()

    await seed_tourism(force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
