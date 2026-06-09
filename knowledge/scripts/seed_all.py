"""
Weatherise v2 — Database Seeder
Seeds all knowledge into:
  - Qdrant: vector embeddings for RAG
  - PostgreSQL: schema creation
  
Run: python3 knowledge/scripts/seed_all.py
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct
)
import httpx

# ── Config ──────────────────────────────────────────────────
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
NIM_EMBED_URL = os.getenv("NIM_EMBED_BASE_URL", "http://localhost:8002/v1")
NIM_EMBED_MODEL = os.getenv("NIM_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
EMBED_DIM = 1024  # nv-embedqa-e5-v5 dimension
SEED_DIR = REPO_ROOT / "knowledge" / "seed_data"

# ── Collections ──────────────────────────────────────────────
COLLECTIONS = {
    "tourism_knowledge": {
        "files": [
            SEED_DIR / "tourism" / "danang_locations.json",
        ],
        "text_fields": ["name", "description", "category", "highlights"],
    },
    "construction_knowledge": {
        "files": [
            SEED_DIR / "construction" / "danang_sites.json",
        ],
        "text_fields": ["site_name", "project_type", "city"],
    },
    "agriculture_knowledge": {
        "files": [
            SEED_DIR / "agriculture" / "agriculture_rules.json",
        ],
        "text_fields": ["content", "topic", "keywords"],
    },
    "weather_rules": {
        "files": [
            SEED_DIR / "shared" / "weather_rules.json",
        ],
        "text_fields": ["content", "topic", "domain"],
    },
}

# ── Helpers ──────────────────────────────────────────────────
def make_text(item: dict, fields: list[str]) -> str:
    parts = []
    for f in fields:
        v = item.get(f)
        if isinstance(v, list):
            parts.append(" ".join(str(x) for x in v))
        elif v:
            parts.append(str(v))
    return " | ".join(parts)


async def embed_batch(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    """Call NIM Embed API for a batch of texts."""
    r = await client.post(
        f"{NIM_EMBED_URL}/embeddings",
        json={"input": texts, "model": NIM_EMBED_MODEL, "input_type": "passage"},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    return [d["embedding"] for d in data["data"]]


async def load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  ⚠️  File not found: {path}")
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


async def seed_collection(
    name: str,
    config: dict,
    qdrant: AsyncQdrantClient,
    http: httpx.AsyncClient,
):
    print(f"\n📂 Seeding collection: {name}")

    # Load all items
    items = []
    for file_path in config["files"]:
        loaded = await load_json(file_path)
        items.extend(loaded)
        print(f"  Loaded {len(loaded)} items from {file_path.name}")

    if not items:
        print("  ⚠️  No items to index, skipping.")
        return

    # Create or recreate collection
    existing = [c.name for c in (await qdrant.get_collections()).collections]
    if name in existing:
        print(f"  🗑  Dropping existing collection {name}...")
        await qdrant.delete_collection(name)

    await qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )
    print(f"  ✅ Collection {name} created (dim={EMBED_DIM})")

    # Embed in batches of 16
    BATCH = 16
    points = []
    for i in range(0, len(items), BATCH):
        batch = items[i : i + BATCH]
        texts = [make_text(item, config["text_fields"]) for item in batch]
        embeddings = await embed_batch(texts, http)
        for j, (item, emb) in enumerate(zip(batch, embeddings)):
            pid = i + j
            # Use existing id or auto-generate
            payload = {k: v for k, v in item.items() if k != "embedding"}
            point_id = item.get("id") or item.get("site_id") or item.get("destination_id") or str(pid)
            # Qdrant needs int or UUID — convert string id to int hash
            import hashlib
            int_id = int(hashlib.md5(str(point_id).encode()).hexdigest()[:8], 16)
            points.append(PointStruct(id=int_id, vector=emb, payload=payload))
        print(f"  Embedded {min(i + BATCH, len(items))}/{len(items)} items...")

    # Upsert
    await qdrant.upsert(collection_name=name, points=points, wait=True)
    count = (await qdrant.get_collection(name)).points_count
    print(f"  ✅ {count} vectors indexed in '{name}'")


async def setup_postgres():
    """Create PostgreSQL schema."""
    import asyncpg

    POSTGRES_URL = os.getenv(
        "POSTGRES_URL",
        "postgresql://weatherise:weatherise@localhost:5432/weatherise"
    )
    try:
        conn = await asyncpg.connect(POSTGRES_URL)
        print("\n🐘 Setting up PostgreSQL schema...")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                updated_at  TIMESTAMPTZ DEFAULT NOW(),
                domain      TEXT,
                location    TEXT,
                message_count INTEGER DEFAULT 0
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id          BIGSERIAL PRIMARY KEY,
                session_id  TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                raw_input   TEXT NOT NULL,
                domain      TEXT,
                location    TEXT,
                overall_risk TEXT,
                final_answer TEXT,
                latency_ms  INTEGER,
                status      TEXT DEFAULT 'success'
            );
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_domain  ON query_logs(domain);
            CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
        """)

        await conn.close()
        print("  ✅ Tables: sessions, query_logs")
        print("  ✅ Indexes created")
    except Exception as e:
        print(f"  ⚠️  Postgres setup error: {e}")


async def main():
    print("=" * 55)
    print("  Weatherise v2 — Database Seeder")
    print("=" * 55)
    print(f"  Qdrant  : {QDRANT_URL}")
    print(f"  NIM Embed: {NIM_EMBED_URL}")
    print(f"  Model   : {NIM_EMBED_MODEL}")

    # Setup Postgres
    await setup_postgres()

    # Seed Qdrant
    qdrant = AsyncQdrantClient(url=QDRANT_URL)
    async with httpx.AsyncClient() as http:
        # Verify NIM embed is reachable
        try:
            r = await http.get(f"{NIM_EMBED_URL}/models", timeout=5.0)
            r.raise_for_status()
            print(f"\n✅ NIM Embed reachable")
        except Exception as e:
            print(f"\n❌ NIM Embed not reachable: {e}")
            print("   → Seeding aborted. Start NIM Embed container first.")
            return

        for col_name, col_config in COLLECTIONS.items():
            try:
                await seed_collection(col_name, col_config, qdrant, http)
            except Exception as e:
                print(f"  ❌ Error seeding {col_name}: {e}")

    # Summary
    print("\n" + "=" * 55)
    print("  Seeding complete! Collections:")
    collections = await qdrant.get_collections()
    for c in collections.collections:
        info = await qdrant.get_collection(c.name)
        print(f"    {c.name:<30} {info.points_count} vectors")
    print("=" * 55)

    await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
