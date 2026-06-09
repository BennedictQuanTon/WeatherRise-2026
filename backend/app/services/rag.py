"""
Milvus RAG Service — Phase 4 Step 4 Tier 1
===========================================
Asynchronous vector similarity search against domain-specific Milvus collections
using the nv-embedqa-e5-v5 embedding model on GPU 4.

Design contract (per context_agents_flow.md Step 4):
  - Execute async vector search against the assigned collection
  - Fetch static parameters, structural safety margins, and coordinates from metadata
  - Return None on empty result or connection timeout (triggers Tier 2 MCP fallback)
"""

from __future__ import annotations

import logging
from typing import Optional

from ..configs.settings import settings

logger = logging.getLogger("uvicorn.error")


class MilvusRAGService:
    """
    Async Milvus client for hybrid vector similarity search.

    Embedding model: nv-embedqa-e5-v5 (on GPU 4 of the H200 cluster)
    Collections: tourism_collection, fishery_collection, construction_collection

    Returns the top-1 metadata dict on hit, None on empty result or timeout.
    """

    def __init__(self) -> None:
        self._embed_client = None
        self._milvus_client = None

    def _get_embed_client(self):
        """Lazily initialize the embedding client targeting NIM embed endpoint."""
        if self._embed_client is not None:
            return self._embed_client

        try:
            from openai import AsyncOpenAI

            self._embed_client = AsyncOpenAI(
                base_url=settings.NIM_EMBED_BASE_URL,
                api_key=settings.NGC_API_KEY or "nim-local",
            )
            logger.info(
                "[RAG] Embedding client ready | base_url=%s | model=%s",
                settings.NIM_EMBED_BASE_URL,
                settings.NIM_EMBED_MODEL,
            )
        except ImportError:
            logger.warning("[RAG] openai SDK not installed — embedding unavailable")

        return self._embed_client

    async def _embed(self, text: str) -> list[float]:
        """
        Generate a dense vector for the extraction_key string
        using nv-embedqa-e5-v5 on GPU 4.
        """
        client = self._get_embed_client()
        if client is None:
            raise RuntimeError("Embedding client not available")

        response = await client.embeddings.create(
            input=text,
            model=settings.NIM_EMBED_MODEL,
        )
        return response.data[0].embedding

    async def _get_milvus_client(self):
        """Lazily initialize the async Milvus client."""
        if self._milvus_client is not None:
            return self._milvus_client

        try:
            from pymilvus import AsyncMilvusClient

            self._milvus_client = AsyncMilvusClient(
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            logger.info(
                "[RAG] Milvus client ready | host=%s | port=%s",
                settings.MILVUS_HOST,
                settings.MILVUS_PORT,
            )
        except ImportError:
            logger.warning("[RAG] pymilvus not installed — Milvus search unavailable")

        return self._milvus_client

    async def query(
        self, collection: str, extraction_key: str
    ) -> Optional[dict]:
        """
        Execute async vector similarity search against the specified Milvus collection.

        Args:
            collection: One of the three domain collection names from settings.
            extraction_key: The entity string from the discriminator (place name, ID, etc.)

        Returns:
            Top-1 metadata dict from the collection on hit.
            None if the result is empty, the collection is unreachable, or a timeout fires.
        """
        import asyncio

        try:
            # Step 1: Embed the extraction_key
            query_vector = await asyncio.wait_for(
                self._embed(extraction_key),
                timeout=settings.MILVUS_TIMEOUT_SECONDS,
            )

            # Step 2: Execute vector similarity search
            client = await asyncio.wait_for(
                self._get_milvus_client(),
                timeout=settings.MILVUS_TIMEOUT_SECONDS,
            )

            if client is None:
                logger.warning("[RAG] No Milvus client — returning None (→ Tier 2)")
                return None

            results = await asyncio.wait_for(
                client.search(
                    collection_name=collection,
                    data=[query_vector],
                    limit=settings.MILVUS_SEARCH_TOP_K,
                    output_fields=["*"],  # Fetch all metadata fields
                ),
                timeout=settings.MILVUS_TIMEOUT_SECONDS,
            )

            # Step 3: Evaluate result
            if not results or not results[0]:
                logger.info(
                    "[RAG] Empty result | collection=%s | key=%s → Tier 2",
                    collection,
                    extraction_key,
                )
                return None

            top_hit = results[0][0]
            metadata: dict = top_hit.get("entity", {})

            logger.info(
                "[RAG] Hit | collection=%s | key=%s | score=%.4f",
                collection,
                extraction_key,
                top_hit.get("distance", 0.0),
            )
            return metadata

        except asyncio.TimeoutError:
            logger.warning(
                "[RAG] Timeout | collection=%s | key=%s → Tier 2",
                collection,
                extraction_key,
            )
            return None

        except Exception as exc:
            logger.error(
                "[RAG] Error during search | collection=%s | error=%s → Tier 2",
                collection,
                exc,
            )
            return None


# Module-level singleton
milvus_rag = MilvusRAGService()
