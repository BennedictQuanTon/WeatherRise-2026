"""
Weather normalizer.
Routes weather source → correct adapter → produces CanonicalWeatherData.
For MVP, only routes to OpenMeteoAdapter.
Future: can route to Earth2Adapter or other sources.
"""

from typing import Any

from .adapters.open_meteo_adapter import OpenMeteoAdapter
from .schemas import CanonicalWeatherData


class WeatherNormalizer:
    """Routes raw weather bundles to the correct adapter and returns canonical data."""

    def __init__(self):
        self._adapters = {
            "open_meteo": OpenMeteoAdapter(),
        }

    def normalize(
        self,
        raw_bundle: dict[str, Any],
        context: dict[str, Any],
    ) -> CanonicalWeatherData:
        """
        Convert a raw weather bundle into CanonicalWeatherData.

        Args:
            raw_bundle: {"source": "open_meteo" | "earth2" | ..., "raw": {...}}
            context: {"location": {...}, "forecast_window": {...}}

        Returns:
            Validated CanonicalWeatherData model.

        Raises:
            ValueError: if no adapter is registered for the source.
        """
        source = raw_bundle.get("source", "unknown")

        adapter = self._adapters.get(source)
        if adapter is None:
            raise ValueError(
                f"No adapter registered for weather source: {source}. "
                f"Available: {list(self._adapters.keys())}"
            )

        canonical_dict = adapter.to_canonical(raw_bundle, context)
        return CanonicalWeatherData(**canonical_dict)
