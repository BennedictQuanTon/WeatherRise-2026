"""Source-specific normalizers for Path B."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from .schemas import RawWeatherResponse, StandardWeatherRecord, WeatherRequirement


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percent_to_prob(value: Any) -> float | None:
    if value is None:
        return None
    try:
        prob = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, prob / 100.0))

def _ratio_to_prob(value: Any) -> float | None:
    if value is None:
        return None
    try:
        prob = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, prob))


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ms_to_kmh(value: Any) -> float | None:
    number = _num(value)
    return None if number is None else round(number * 3.6, 3)


def _meters_to_km(value: Any) -> float | None:
    number = _num(value)
    return None if number is None else round(number / 1000.0, 3)


def _record(
    raw: RawWeatherResponse,
    requirement: WeatherRequirement,
    forecast_time: str | None,
    **values: Any,
) -> StandardWeatherRecord:
    time_value = forecast_time or requirement.start_time or _utc_now()
    return StandardWeatherRecord(
        request_id=requirement.request_id,
        source_code=raw.source_code,
        location_name=requirement.location_name,
        latitude=requirement.latitude,
        longitude=requirement.longitude,
        forecast_time_utc=time_value,
        forecast_time_local=time_value,
        fetched_at_utc=raw.fetched_at_utc,
        raw_file_path=raw.raw_file_path,
        **values,
    )


class BaseWeatherNormalizer:
    source_code = "base"

    def normalize(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        if raw.status != "success" or not raw.raw_payload:
            return []
        return self._normalize_payload(raw, requirement)

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        raise NotImplementedError


class OpenMeteoNormalizer(BaseWeatherNormalizer):
    source_code = "open_meteo"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        records = []
        for idx, time_value in enumerate(times):
            records.append(
                _record(
                    raw,
                    requirement,
                    time_value,
                    temperature_c=_at(hourly.get("temperature_2m"), idx),
                    humidity_percent=_at(hourly.get("relative_humidity_2m"), idx),
                    precipitation_mm=_at(hourly.get("precipitation"), idx),
                    rain_probability=_percent_to_prob(_at(hourly.get("precipitation_probability"), idx)),
                    wind_speed_kmh=_at(hourly.get("wind_speed_10m"), idx),
                    wind_gust_kmh=_at(hourly.get("wind_gusts_10m"), idx),
                    wind_direction_deg=_at(hourly.get("wind_direction_10m"), idx),
                    cloud_cover_percent=_at(hourly.get("cloud_cover"), idx),
                )
            )
        return records[:168]


class WeatherAPINormalizer(BaseWeatherNormalizer):
    source_code = "weatherapi"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        current = payload.get("current") or {}
        alerts = ((payload.get("alerts") or {}).get("alert") or [])
        records: list[StandardWeatherRecord] = []
        forecast_days = (payload.get("forecast") or {}).get("forecastday") or []
        for day in forecast_days:
            day_rain = ((day.get("day") or {}).get("daily_chance_of_rain"))
            for hour in day.get("hour") or []:
                records.append(
                    _record(
                        raw,
                        requirement,
                        hour.get("time"),
                        temperature_c=_num(hour.get("temp_c")),
                        feels_like_c=_num(hour.get("feelslike_c")),
                        humidity_percent=_num(hour.get("humidity")),
                        precipitation_mm=_num(hour.get("precip_mm")),
                        rain_probability=_percent_to_prob(hour.get("chance_of_rain", day_rain)),
                        wind_speed_kmh=_num(hour.get("wind_kph")),
                        wind_gust_kmh=_num(hour.get("gust_kph")),
                        wind_direction_deg=_num(hour.get("wind_degree")),
                        pressure_hpa=_num(hour.get("pressure_mb")),
                        visibility_km=_num(hour.get("vis_km")),
                        cloud_cover_percent=_num(hour.get("cloud")),
                        uv_index=_num(hour.get("uv")),
                        weather_code=(hour.get("condition") or {}).get("code"),
                        weather_description=(hour.get("condition") or {}).get("text"),
                        alerts=alerts,
                    )
                )
        if not records and current:
            records.append(
                _record(
                    raw,
                    requirement,
                    current.get("last_updated"),
                    temperature_c=_num(current.get("temp_c")),
                    feels_like_c=_num(current.get("feelslike_c")),
                    humidity_percent=_num(current.get("humidity")),
                    precipitation_mm=_num(current.get("precip_mm")),
                    wind_speed_kmh=_num(current.get("wind_kph")),
                    wind_gust_kmh=_num(current.get("gust_kph")),
                    wind_direction_deg=_num(current.get("wind_degree")),
                    pressure_hpa=_num(current.get("pressure_mb")),
                    visibility_km=_num(current.get("vis_km")),
                    cloud_cover_percent=_num(current.get("cloud")),
                    uv_index=_num(current.get("uv")),
                    weather_code=(current.get("condition") or {}).get("code"),
                    weather_description=(current.get("condition") or {}).get("text"),
                    alerts=alerts,
                )
            )
        return records[:168]


class TomorrowIONormalizer(BaseWeatherNormalizer):
    source_code = "tomorrow_io"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        timelines = payload.get("timelines") or {}
        intervals = timelines.get("hourly") or timelines.get("minutely") or []
        if isinstance(intervals, dict):
            intervals = intervals.get("intervals") or []
        records = []
        for item in intervals:
            values = item.get("values") or {}
            records.append(
                _record(
                    raw,
                    requirement,
                    item.get("time") or item.get("startTime"),
                    temperature_c=_num(values.get("temperature")),
                    feels_like_c=_num(values.get("temperatureApparent")),
                    humidity_percent=_num(values.get("humidity")),
                    precipitation_mm=_num(values.get("rainIntensity") or values.get("precipitationIntensity")),
                    rain_probability=_percent_to_prob(values.get("precipitationProbability")),
                    wind_speed_kmh=_ms_to_kmh(values.get("windSpeed")),
                    wind_gust_kmh=_ms_to_kmh(values.get("windGust")),
                    wind_direction_deg=_num(values.get("windDirection")),
                    pressure_hpa=_num(values.get("pressureSurfaceLevel")),
                    visibility_km=_num(values.get("visibility")),
                    cloud_cover_percent=_num(values.get("cloudCover")),
                    uv_index=_num(values.get("uvIndex")),
                    weather_code=values.get("weatherCode"),
                )
            )
        return records[:168]


class VisualCrossingNormalizer(BaseWeatherNormalizer):
    source_code = "visual_crossing"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        alerts = payload.get("alerts") or []
        records = []
        for day in payload.get("days") or []:
            hours = day.get("hours") or []
            if not hours:
                hours = [day]
            for hour in hours:
                time_value = hour.get("datetime")
                if time_value and day.get("datetime") and "T" not in time_value:
                    time_value = f"{day.get('datetime')}T{time_value}"
                records.append(
                    _record(
                        raw,
                        requirement,
                        time_value,
                        temperature_c=_num(hour.get("temp")),
                        feels_like_c=_num(hour.get("feelslike")),
                        humidity_percent=_num(hour.get("humidity")),
                        precipitation_mm=_num(hour.get("precip")),
                        rain_probability=_percent_to_prob(hour.get("precipprob")),
                        wind_speed_kmh=_num(hour.get("windspeed")),
                        wind_gust_kmh=_num(hour.get("windgust")),
                        wind_direction_deg=_num(hour.get("winddir")),
                        pressure_hpa=_num(hour.get("pressure")),
                        visibility_km=_num(hour.get("visibility")),
                        cloud_cover_percent=_num(hour.get("cloudcover")),
                        uv_index=_num(hour.get("uvindex")),
                        weather_code=hour.get("icon"),
                        weather_description=hour.get("conditions"),
                        alerts=alerts,
                    )
                )
        return records[:168]


class OpenWeatherMapNormalizer(BaseWeatherNormalizer):
    source_code = "openweathermap"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        items = payload.get("list") or [payload]
        records = []
        for item in items:
            main = item.get("main") or {}
            wind = item.get("wind") or {}
            weather = (item.get("weather") or [{}])[0]
            clouds = item.get("clouds") or {}
            rain = item.get("rain") or {}
            records.append(
                _record(
                    raw,
                    requirement,
                    item.get("dt_txt"),
                    temperature_c=_num(main.get("temp")),
                    feels_like_c=_num(main.get("feels_like")),
                    humidity_percent=_num(main.get("humidity")),
                    precipitation_mm=_num(rain.get("1h") or rain.get("3h")),
                    rain_probability=_ratio_to_prob(item.get("pop")),
                    wind_speed_kmh=_ms_to_kmh(wind.get("speed")),
                    wind_gust_kmh=_ms_to_kmh(wind.get("gust")),
                    wind_direction_deg=_num(wind.get("deg")),
                    pressure_hpa=_num(main.get("pressure")),
                    visibility_km=_meters_to_km(item.get("visibility")),
                    cloud_cover_percent=_num(clouds.get("all")),
                    weather_code=weather.get("id"),
                    weather_description=weather.get("description"),
                )
            )
        return records[:168]


class SevenTimerNormalizer(BaseWeatherNormalizer):
    source_code = "seven_timer"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        init = payload.get("init")
        base_time = _parse_7timer_init(init)
        records = []
        for item in payload.get("dataseries") or []:
            forecast_time = None
            if base_time and item.get("timepoint") is not None:
                forecast_time = (base_time + timedelta(hours=int(item["timepoint"]))).isoformat()
            wind = item.get("wind10m") or {}
            records.append(
                _record(
                    raw,
                    requirement,
                    forecast_time,
                    temperature_c=_num(item.get("temp2m")),
                    humidity_percent=_num(item.get("rh2m")),
                    wind_speed_kmh=_seven_timer_wind_speed(wind),
                    weather_code=item.get("weather"),
                    weather_description=str(item.get("weather")) if item.get("weather") else None,
                )
            )
        return records[:168]


class StormglassNormalizer(BaseWeatherNormalizer):
    source_code = "stormglass"

    def _normalize_payload(self, raw: RawWeatherResponse, requirement: WeatherRequirement) -> list[StandardWeatherRecord]:
        payload = raw.raw_payload or {}
        records = []
        for item in payload.get("hours") or []:
            records.append(
                _record(
                    raw,
                    requirement,
                    item.get("time"),
                    temperature_c=_first_provider_value(item.get("airTemperature")),
                    wind_speed_kmh=_ms_to_kmh(_first_provider_value(item.get("windSpeed"))),
                    wind_gust_kmh=_ms_to_kmh(_first_provider_value(item.get("windGust"))),
                    wave_height_m=_first_provider_value(item.get("waveHeight")),
                    water_temperature_c=_first_provider_value(item.get("waterTemperature")),
                )
            )
        tides = ((payload.get("tide") or {}).get("data") or payload.get("tides") or [])
        if records and tides:
            records[0].tide_height_m = _num(tides[0].get("height"))
            records[0].tide_type = tides[0].get("type")
        return records[:168]


NORMALIZERS: dict[str, BaseWeatherNormalizer] = {
    "open_meteo": OpenMeteoNormalizer(),
    "weatherapi": WeatherAPINormalizer(),
    "tomorrow_io": TomorrowIONormalizer(),
    "visual_crossing": VisualCrossingNormalizer(),
    "openweathermap": OpenWeatherMapNormalizer(),
    "seven_timer": SevenTimerNormalizer(),
    "stormglass": StormglassNormalizer(),
}


class SourceSpecificNormalizer:
    """Dispatches raw responses to source-specific normalizers."""

    def __init__(self, normalizers: dict[str, BaseWeatherNormalizer] | None = None):
        self.normalizers = normalizers or NORMALIZERS

    def normalize(
        self,
        raw_responses: Iterable[RawWeatherResponse],
        requirement: WeatherRequirement,
    ) -> list[StandardWeatherRecord]:
        records: list[StandardWeatherRecord] = []
        for raw in raw_responses:
            normalizer = self.normalizers.get(raw.source_code)
            if not normalizer:
                continue
            records.extend(normalizer.normalize(raw, requirement))
        return records


def _at(values: Any, idx: int) -> float | None:
    if not isinstance(values, list) or idx >= len(values):
        return None
    return _num(values[idx])





def _parse_7timer_init(init: Any) -> datetime | None:
    if not init:
        return None
    try:
        return datetime.strptime(str(init), "%Y%m%d%H").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _seven_timer_wind_speed(wind: dict[str, Any]) -> float | None:
    speed = wind.get("speed") or wind.get("windspeed")
    if isinstance(speed, str):
        scale = {
            "calm": 2.0,
            "light": 10.0,
            "moderate": 20.0,
            "fresh": 30.0,
            "strong": 45.0,
        }
        return scale.get(speed.lower())
    return _num(speed)


def _first_provider_value(value: Any) -> float | None:
    if isinstance(value, dict):
        for provider in ("sg", "noaa", "meteo", "dwd", "icon"):
            if provider in value:
                return _num(value[provider])
    return _num(value)
