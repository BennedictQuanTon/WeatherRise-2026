"""
RAG Ingestion Pipeline — V3
Fire-and-forget pipeline: places → embed → upsert Qdrant → upsert Postgres.
Called after Overpass live fetch (Tier 3) to enrich KB for future queries.
Idempotent: upsert by place_id — no duplicates.
"""
import asyncio
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from knowledge.vector_store.client import VectorStoreClient, embed_texts
from knowledge.vector_store.collections import COLLECTIONS

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://weatherise:weatherise@localhost:5432/weatherise")


# Fields used to build the embedding text per domain
TEXT_FIELDS: Dict[str, List[str]] = {
    "tourism": ["name_vi", "name_en", "sub_category", "highlights", "vibe_tags", "city"],
    "construction": ["name", "description", "hazard_type", "location"],
    "agriculture": ["name", "crop_type", "location", "notes"],
}


def _make_text(place: Dict, fields: List[str]) -> str:
    """Concatenate relevant fields for embedding."""
    parts = []
    for f in fields:
        val = place.get(f)
        if val:
            parts.append(str(val) if not isinstance(val, list) else " ".join(val))
    return " | ".join(parts)


def _place_id_to_int(place_id: str) -> int:
    """Convert string place_id → stable int for Qdrant point ID."""
    return int(hashlib.md5(place_id.encode()).hexdigest(), 16) % (2**63)


async def async_ingest_places(
    places: List[Dict],
    domain: str = "tourism",
    source: str = "osm_live",
) -> None:
    """
    Async ingest places into Qdrant + PostgreSQL.
    Designed as fire-and-forget — errors are logged, not raised.

    Args:
        places: List of V3 place dicts (must have 'place_id', 'latitude', 'longitude')
        domain: Knowledge domain ("tourism" | "construction" | "agriculture")
        source: Data source label for provenance tracking
    """
    if not places:
        return

    collection_name = f"{domain}_knowledge"
    fields = TEXT_FIELDS.get(domain, ["name_vi", "name_en"])
    vs = VectorStoreClient()

    try:
        # 0. Ensure collection exists
        col_config = COLLECTIONS.get(collection_name, {})
        await vs.ensure_collection(
            collection=collection_name,
            vector_size=col_config.get("vector_size", 1024),
        )

        # 1. Build embedding texts
        texts = [_make_text(p, fields) for p in places]

        # 2. Embed in batches
        embeddings = await embed_texts(texts)

        # 3. Build Qdrant point structs
        now = datetime.now().isoformat()
        points = []
        for place, emb in zip(places, embeddings):
            pid = place.get("place_id", "")
            if not pid:
                continue
            points.append({
                "id": _place_id_to_int(pid),
                "vector": emb,
                "payload": {
                    **place,
                    "ingested_at": now,
                    "ingest_source": source,
                    "domain": domain,
                },
            })

        # 4. Upsert into Qdrant
        ok = await vs.upsert(collection=collection_name, points=points)
        if ok:
            print(f"[Ingestion] ✅ Qdrant upsert: {len(points)} places → '{collection_name}'")
        else:
            print(f"[Ingestion] ⚠️ Qdrant upsert returned failure for '{collection_name}'")

        # 5. Upsert into PostgreSQL (best effort)
        await _upsert_postgres(places, source=source, domain=domain)

    except Exception as e:
        # Never crash the request that triggered ingestion
        print(f"[Ingestion] ❌ Failed: {e}")


async def _upsert_postgres(
    places: List[Dict],
    source: str,
    domain: str,
) -> None:
    """Upsert places into PostgreSQL locations table (best effort)."""
    try:
        import asyncpg
        conn = await asyncpg.connect(POSTGRES_URL)
        now = datetime.now()
        inserted = 0

        for p in places:
            place_id = p.get("place_id")
            name_vi = p.get("name_vi", "")
            lat = p.get("latitude")
            lon = p.get("longitude")
            if not (place_id and lat and lon):
                continue

            # Deduplication: check for similar name within 30 meters
            try:
                dup_id = await conn.fetchval("""
                    SELECT id 
                    FROM locations 
                    WHERE (
                        lower(name_vi) = lower($1) 
                        OR lower(name_en) = lower($1)
                        OR lower(name_vi) LIKE '%' || lower($1) || '%'
                        OR lower($1) LIKE '%' || lower(name_vi) || '%'
                    )
                    AND ST_DWithin(
                        coordinate,
                        ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography,
                        30
                    )
                    LIMIT 1
                """, name_vi, float(lon), float(lat))
                
                if dup_id and dup_id != place_id:
                    if source == "google_maps_scrape" and not dup_id.startswith("gmaps_"):
                        # Overwrite: Delete old duplicate so the high-quality GMaps record is inserted instead
                        await conn.execute("DELETE FROM locations WHERE id = $1", dup_id)
                        print(f"[Ingestion] Deduplicated: Deleted old duplicate '{dup_id}' to prefer GMaps record")
            except Exception as spatial_err:
                print(f"[Ingestion] Spatial duplicate check warning: {spatial_err}")

            await conn.execute("""
                INSERT INTO locations (
                    id, name_vi, name_en, category, sub_category,
                    city, latitude, longitude,
                    is_indoor, vibe_tags, source,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$12)
                ON CONFLICT (id) DO UPDATE SET
                    name_vi = EXCLUDED.name_vi,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    updated_at = EXCLUDED.updated_at
            """,
                place_id,
                name_vi,
                p.get("name_en", name_vi),
                p.get("category", domain),
                p.get("sub_category", ""),
                p.get("city", ""),
                float(lat),
                float(lon),
                p.get("is_indoor", False),
                p.get("vibe_tags", []),
                source,
                now,
            )
            inserted += 1

        await conn.close()
        print(f"[Ingestion] ✅ Postgres upsert: {inserted} places")

    except Exception as e:
        # Postgres failure doesn't block — Qdrant is primary
        print(f"[Ingestion] ⚠️ Postgres upsert skipped: {e}")
