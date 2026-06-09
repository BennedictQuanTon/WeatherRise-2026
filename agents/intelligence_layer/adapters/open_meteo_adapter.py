"""
Open-Meteo adapter.
Converts raw Open-Meteo API response into Canonical Weather JSON.

Mapping:
  Open-Meteo field           → Canonical field
  temperature_2m             → temperature_c
  relative_humidity_2m       → humidity_percent
  precipitation_probability  → rain_probability
  precipitation              → precipitation_mm
  wind_speed_10m             → wind_speed_kmh
  wind_gusts_10m             → wind_gust_kmh
  weather_code               → weather_code
"""

from typing import Any


class OpenMeteoAdapter:
    """Maps raw Open-Meteo response into the stable Canonical Weather JSON."""

    def to_canonical(
        self,
        raw_bundle: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convert raw Open-Meteo response to Canonical Weather JSON.

        Args:
            raw_bundle: {"source": "open_meteo", "raw": {...}, "request": {...}}
            context: {"location": {...}, "forecast_window": {...}}

        Returns:
            Canonical Weather JSON dict matching CanonicalWeatherData schema.
        """
        raw = raw_bundle["raw"]
        hourly = raw.get("hourly", {})
        times = hourly.get("time", [])

        variables = []
        for idx, time_value in enumerate(times):
            variables.append({
                "time": time_value,
                "temperature_c": _safe_get(hourly, "temperature_2m", idx),
                "rain_probability": _safe_get(hourly, "precipitation_probability", idx),
                "precipitation_mm": _safe_get(hourly, "precipitation", idx),
                "wind_speed_kmh": _safe_get(hourly, "wind_speed_10m", idx),
                "wind_gust_kmh": _safe_get(hourly, "wind_gusts_10m", idx),
                "humidity_percent": _safe_get(hourly, "relative_humidity_2m", idx),
                "weather_code": _safe_get(hourly, "weather_code", idx),
                "storm_risk": None,
            })

        missing_fields = []
        for field in ["temperature_2m", "precipitation_probability", "wind_speed_10m"]:
            if field not in hourly or not hourly[field]:
                missing_fields.append(field)

        return {
            "source": "open_meteo",
            "source_type": "api_forecast",
            "location": context["location"],
            "forecast_window": context["forecast_window"],
            "resolution": {
                "temporal": "hourly",
                "spatial": "city_level",
            },
            "variables": variables,
            "data_quality": {
                "missing_fields": missing_fields,
                "confidence": "medium" if not missing_fields else "low",
                "notes": ["Normalized from Open-Meteo hourly forecast."],
            },
        }


def _safe_get(hourly: dict, key: str, idx: int) -> Any:
    """Safely get a value from hourly arrays by index."""
    values = hourly.get(key)
    if not values or idx >= len(values):
        return None
    return values[idx]
