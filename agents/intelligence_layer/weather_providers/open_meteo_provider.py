"""
Open-Meteo weather provider.
Fetches raw hourly forecast data from the free Open-Meteo API.
"""

import httpx
from typing import Any
from .base import WeatherProvider


class OpenMeteoProvider(WeatherProvider):
    """Fetches weather data from Open-Meteo API (free, no API key required)."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    HOURLY_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation_probability",
        "precipitation",
        "wind_speed_10m",
        "wind_gusts_10m",
        "weather_code",
    ]

    async def fetch(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Fetch raw hourly weather forecast from Open-Meteo.

        Args:
            request: dict with latitude, longitude, timezone, forecast_days

        Returns:
            {"source": "open_meteo", "raw": <api_response>, "request": <original_request>}
        """
        params = {
            "latitude": request["latitude"],
            "longitude": request["longitude"],
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "timezone": request.get("timezone", "Asia/Ho_Chi_Minh"),
            "forecast_days": request.get("forecast_days", 7),
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        return {
            "source": "open_meteo",
            "raw": data,
            "request": request,
        }
