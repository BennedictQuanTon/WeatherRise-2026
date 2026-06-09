"""
MCP Route: weather.getForecast
Retrieves weather forecast from Open-Meteo (no API key needed).
Cache: 30-60 minutes.
"""
import httpx
import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter()
OPEN_METEO_BASE = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")

# Simple TTL cache
CACHE: Dict[str, Any] = {}


class ForecastRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.post("/getForecast")
async def get_forecast(req: ForecastRequest):
    cache_key = f"forecast:{req.latitude:.3f}:{req.longitude:.3f}:{req.start_date}:{req.end_date}"
    if cache_key in CACHE:
        return CACHE[cache_key]

    params = {
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timezone": "Asia/Ho_Chi_Minh",
        "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,relative_humidity_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,weather_code",
        "forecast_days": 7,
    }
    if req.start_date:
        params["start_date"] = req.start_date
    if req.end_date:
        params["end_date"] = req.end_date

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{OPEN_METEO_BASE}/forecast", params=params)
            r.raise_for_status()
            data = r.json()

        CACHE[cache_key] = data
        return data

    except Exception as e:
        print(f"[MCP:weather.forecast] Error: {e}")
        return {"error": str(e), "source": "open-meteo"}


@router.post("/getRealtimeWeather")
async def get_realtime_weather(req: ForecastRequest):
    """Get current weather from OpenWeatherMap."""
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    if not api_key:
        # Fallback: use Open-Meteo current
        return await get_forecast(req)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": req.latitude,
                    "lon": req.longitude,
                    "appid": api_key,
                    "units": "metric",
                },
            )
            r.raise_for_status()
            data = r.json()

        return {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"] * 3.6,  # m/s → km/h
            "weather_condition": data["weather"][0]["description"],
            "weather_code": data["weather"][0]["id"],
            "rain_probability": data.get("rain", {}).get("1h", 0) * 10,  # rough estimate
            "source": "openweathermap",
        }
    except Exception as e:
        print(f"[MCP:weather.realtime] Error: {e}")
        return {"error": str(e)}
