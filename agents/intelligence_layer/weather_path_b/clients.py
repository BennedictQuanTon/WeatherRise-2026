"""Provider clients for Path B multi-source weather fetching."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .config.source_registry import SourceConfig
from .schemas import RawWeatherResponse, WeatherRequirement


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseWeatherClient:
    source_code = "base"

    def __init__(self, config: SourceConfig):
        self.config = config

    async def fetch(self, requirement: WeatherRequirement) -> RawWeatherResponse:
        start = time.perf_counter()
        try:
            payload = await self._fetch_payload(requirement)
            return RawWeatherResponse(
                request_id=requirement.request_id,
                source_code=self.source_code,
                status="success",
                raw_payload=payload,
                fetched_at_utc=utc_now_iso(),
                latency_ms=round((time.perf_counter() - start) * 1000),
            )
        except httpx.TimeoutException as exc:
            return self._failure(requirement, "timeout", str(exc), start)
        except Exception as exc:
            return self._failure(requirement, "failed", str(exc), start)

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        raise NotImplementedError

    def _failure(
        self,
        requirement: WeatherRequirement,
        status: str,
        message: str,
        start: float,
    ) -> RawWeatherResponse:
        return RawWeatherResponse(
            request_id=requirement.request_id,
            source_code=self.source_code,
            status=status,  # type: ignore[arg-type]
            raw_payload=None,
            error_message=message,
            fetched_at_utc=utc_now_iso(),
            latency_ms=round((time.perf_counter() - start) * 1000),
        )


class OpenMeteoClient(BaseWeatherClient):
    source_code = "open_meteo"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        url = f"{os.getenv('OPEN_METEO_BASE_URL', 'https://api.open-meteo.com/v1')}/forecast"
        params = {
            "latitude": requirement.latitude,
            "longitude": requirement.longitude,
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "precipitation_probability",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                    "wind_direction_10m",
                    "cloud_cover",
                ]
            ),
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": requirement.timezone,
            "forecast_days": 7,
        }
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class WeatherAPIClient(BaseWeatherClient):
    source_code = "weatherapi"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        key = self.config.api_key()
        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": key,
            "q": f"{requirement.latitude},{requirement.longitude}",
            "days": 7,
            "aqi": "no",
            "alerts": "yes",
        }
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class TomorrowIOClient(BaseWeatherClient):
    source_code = "tomorrow_io"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        key = self.config.api_key()
        url = "https://api.tomorrow.io/v4/weather/forecast"
        params = {
            "apikey": key,
            "location": f"{requirement.latitude},{requirement.longitude}",
            "timesteps": "1h",
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class VisualCrossingClient(BaseWeatherClient):
    source_code = "visual_crossing"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        key = self.config.api_key()
        start = requirement.start_time or "today"
        end = requirement.end_time or start
        url = (
            "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/"
            f"timeline/{requirement.latitude},{requirement.longitude}/{start}/{end}"
        )
        params = {"key": key, "unitGroup": "metric", "include": "days,hours,alerts", "contentType": "json"}
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class OpenWeatherMapClient(BaseWeatherClient):
    source_code = "openweathermap"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        key = self.config.api_key()
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            "appid": key,
            "lat": requirement.latitude,
            "lon": requirement.longitude,
            "units": "metric",
        }
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class SevenTimerClient(BaseWeatherClient):
    source_code = "seven_timer"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        url = "https://www.7timer.info/bin/api.pl"
        params = {
            "lon": requirement.longitude,
            "lat": requirement.latitude,
            "product": "civil",
            "output": "json",
        }
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()


class StormglassClient(BaseWeatherClient):
    source_code = "stormglass"

    async def _fetch_payload(self, requirement: WeatherRequirement) -> dict[str, Any]:
        key = self.config.api_key()
        if not key:
            raise RuntimeError("Stormglass API key is missing")
        url = "https://api.stormglass.io/v2/weather/point"
        params = {
            "lat": requirement.latitude,
            "lng": requirement.longitude,
            "params": "airTemperature,windSpeed,windGust,waveHeight,waterTemperature",
        }
        headers = {"Authorization": key}
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()


CLIENTS: dict[str, type[BaseWeatherClient]] = {
    "open_meteo": OpenMeteoClient,
    "weatherapi": WeatherAPIClient,
    "tomorrow_io": TomorrowIOClient,
    "visual_crossing": VisualCrossingClient,
    "openweathermap": OpenWeatherMapClient,
    "seven_timer": SevenTimerClient,
    "stormglass": StormglassClient,
}
