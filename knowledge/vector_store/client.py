"""
VectorStoreClient — V3
Async Qdrant client with NIM embedding support.
Handles: embed → search → return results with scores.
"""
import os
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
NIM_EMBED_BASE_URL = os.getenv("NIM_EMBED_BASE_URL", "http://localhost:8002/v1")
NIM_EMBED_MODEL = os.getenv("NIM_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
EMBED_BATCH_SIZE = 16


@dataclass
class SearchResult:
    place_id: str
    score: float
    payload: Dict[str, Any]
    source: str = "qdrant_kb"


async def embed_texts(texts: List[str], input_type: str = "passage") -> List[List[float]]:
    """
    Embed texts using NIM NV-EmbedQA-E5-v5 API.
    Returns list of embedding vectors (1024-dim each).
    Batches in groups of EMBED_BATCH_SIZE to respect API limits.
    """
    all_embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i: i + EMBED_BATCH_SIZE]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{NIM_EMBED_BASE_URL}/embeddings",
                    json={"model": NIM_EMBED_MODEL, "input": batch, "input_type": input_type},
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
                embeddings = [item["embedding"] for item in data["data"]]
                all_embeddings.extend(embeddings)
        except Exception as e:
            print(f"[VectorStore] Embed error (batch {i}): {e}")
            # Return zero vectors as fallback (will produce low scores)
            for _ in batch:
                all_embeddings.append([0.0] * 1024)
    return all_embeddings


class VectorStoreClient:
    """Async Qdrant client for KB search operations."""

    def __init__(self):
        self.qdrant_url = QDRANT_URL

    async def search(
        self,
        collection: str,
        query_text: str,
        score_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """
        Embed query_text → cosine search in Qdrant collection.
        Returns results with score ≥ score_threshold.
        """
        try:
            # 1. Embed the query
            embeddings = await embed_texts([query_text], input_type="query")
            vector = embeddings[0]

            # 2. Build Qdrant filter if provided
            qdrant_filter = None
            if filters:
                must_conditions = []
                for key, value in filters.items():
                    if value is not None:
                        must_conditions.append({
                            "key": key,
                            "match": {"value": value}
                        })
                if must_conditions:
                    qdrant_filter = {"must": must_conditions}

            # 3. Search Qdrant
            payload = {
                "vector": vector,
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True,
            }
            if qdrant_filter:
                payload["filter"] = qdrant_filter

            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.qdrant_url}/collections/{collection}/points/search",
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()

            results = []
            for hit in data.get("result", []):
                p = hit.get("payload", {})
                results.append(SearchResult(
                    place_id=p.get("place_id", str(hit.get("id", ""))),
                    score=hit.get("score", 0.0),
                    payload=p,
                    source="qdrant_kb",
                ))
            return results

        except Exception as e:
            print(f"[VectorStore] Search error in '{collection}': {e}")
            return []

    async def collection_exists(self, collection: str) -> bool:
        """Check if a Qdrant collection exists."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.qdrant_url}/collections/{collection}")
                return r.status_code == 200
        except Exception:
            return False

    async def upsert(
        self,
        collection: str,
        points: List[Dict[str, Any]],
    ) -> bool:
        """Upsert points into a Qdrant collection."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.put(
                    f"{self.qdrant_url}/collections/{collection}/points",
                    json={"points": points},
                )
                r.raise_for_status()
                return True
        except Exception as e:
            print(f"[VectorStore] Upsert error: {e}")
            return False

    async def ensure_collection(
        self,
        collection: str,
        vector_size: int = 1024,
    ) -> bool:
        """Create collection if it doesn't exist."""
        if await self.collection_exists(collection):
            return True
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.put(
                    f"{self.qdrant_url}/collections/{collection}",
                    json={
                        "vectors": {
                            "size": vector_size,
                            "distance": "Cosine",
                        }
                    },
                )
                r.raise_for_status()
                print(f"[VectorStore] Created collection: {collection}")
                return True
        except Exception as e:
            print(f"[VectorStore] Create collection error: {e}")
            return False
