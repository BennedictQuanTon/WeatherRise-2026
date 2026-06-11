"""Qdrant/RAG hooks for reusable weather knowledge.

This intentionally performs no writes and does not store live weather numbers.
"""

from __future__ import annotations

from typing import Any

from .schemas import WeatherRequirement


class WeatherKnowledgeRetriever:
    """Placeholder read-only hook for future Qdrant-backed weather knowledge."""

    async def retrieve(self, requirement: WeatherRequirement, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        knowledge: list[dict[str, Any]] = []
        if requirement.activity_type == "beach":
            knowledge.append(
                {
                    "doc_type": "weather_risk_rule",
                    "content": "Beach safety should consider rain, wind, storm alerts, wave height, and tide conditions.",
                    "metadata": {"domain": requirement.domain, "activity_type": "beach"},
                }
            )
        if requirement.domain == "construction":
            knowledge.append(
                {
                    "doc_type": "weather_risk_rule",
                    "content": "Construction operations should use stricter wind and gust interpretation than general tourism.",
                    "metadata": {"domain": "construction"},
                }
            )
        return knowledge
