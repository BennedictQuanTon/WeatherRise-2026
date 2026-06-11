"""
BaseRetriever — V3
Shared logic for all domain retrievers.
Wraps VectorStoreClient with dataclass result types.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from knowledge.vector_store.client import VectorStoreClient, SearchResult

# 3-Tier score thresholds (shared across all retrievers)
SCORE_HIGH = 0.72    # Tier 1: Confident KB match
SCORE_LOW = 0.50     # Tier 2: Possible KB match
MIN_RESULTS = 3      # Minimum results to consider "enough"


@dataclass
class KnowledgeRetrievalResult:
    data: List[Dict[str, Any]]
    source: str                        # "qdrant_kb" | "qdrant_kb_low_confidence" | "osm_live" | "mock_seed"
    confidence: str                    # "high" | "medium" | "low" | "none"
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    search_scores: List[float] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.data) == 0


class BaseRetriever:
    """Base class for all domain-specific retrievers."""

    def __init__(self, collection_name: str):
        self.collection = collection_name
        self.vector_store = VectorStoreClient()

    async def _search_tier1(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Tier 1: Strict search — score ≥ SCORE_HIGH."""
        return await self.vector_store.search(
            collection=self.collection,
            query_text=query,
            score_threshold=SCORE_HIGH,
            filters=filters,
            limit=limit,
        )

    async def _search_tier2(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Tier 2: Relaxed search — score ≥ SCORE_LOW (no location filter)."""
        return await self.vector_store.search(
            collection=self.collection,
            query_text=query,
            score_threshold=SCORE_LOW,
            filters=None,  # Relaxed — no location filter
            limit=limit,
        )

    def _results_to_dicts(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        return [r.payload for r in results]
