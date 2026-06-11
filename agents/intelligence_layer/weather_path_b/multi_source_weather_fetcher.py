"""Parallel multi-source weather fetcher."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .clients import CLIENTS
from .config.source_registry import SourceConfig, get_source_registry
from .schemas import RawWeatherResponse, WeatherRequirement, WeatherSourcePlan


class MultiSourceWeatherFetcher:
    """Calls selected weather clients concurrently with failure isolation."""

    def __init__(self, registry: dict[str, SourceConfig] | None = None, clients: dict | None = None):
        self.registry = registry or get_source_registry()
        self.client_classes = clients or CLIENTS

    async def fetch(self, requirement: WeatherRequirement, plan: WeatherSourcePlan) -> list[RawWeatherResponse]:
        tasks = []
        for item in plan.selected_sources:
            config = self.registry[item.source_code]
            client_cls = self.client_classes.get(item.source_code)
            if not client_cls:
                tasks.append(self._missing_client(requirement, item.source_code))
                continue
            client = client_cls(config)
            tasks.append(client.fetch(requirement))
        return await asyncio.gather(*tasks)

    async def _missing_client(self, requirement: WeatherRequirement, source_code: str) -> RawWeatherResponse:
        return RawWeatherResponse(
            request_id=requirement.request_id,
            source_code=source_code,
            status="failed",
            error_message="No client registered for source",
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        )
