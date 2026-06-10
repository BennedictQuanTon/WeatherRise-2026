"""
Abstract base class for weather data providers.
All providers must implement the `fetch` method.
"""

from abc import ABC, abstractmethod
from typing import Any


class WeatherProvider(ABC):
    """Base class for any weather data source."""

    @abstractmethod
    async def fetch(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Fetch raw weather data from the provider.

        Args:
            request: dict with latitude, longitude, timezone, forecast_days

        Returns:
            dict with {"source": str, "raw": dict, "request": dict}
        """
        raise NotImplementedError
