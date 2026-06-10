"""
MCP Route: weather.getForecast
Phase 1 implementation — wraps Open-Meteo API as a standard MCP tool.
Context Agents call this instead of the Intelligence Layer calling
Open-Meteo directly, centralizing external API access through MCP.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime

router = APIRouter()

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo WMO weather code → human readable
WMO_CODES: Dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Heavy thunderstorm",
}


class ForecastRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: Optional[str] = None   # YYYY-MM-DD, defaults to today
    end_date: Optional[str] = None     # YYYY-MM-DD, defaults to +7 days
    timezone: str = "Asia/Ho_Chi_Minh"


class HourlySnapshot(BaseModel):
    hour: str                  # "08:00"
    temp_c: float
    rain_prob_pct: float
    wind_kmh: float
    humidity_pct: float
    weather_code: int
    weather_label: str
    is_risky: bool             # True if rain_prob > 60% or wind > 40 km/h


class DailyForecast(BaseModel):
    date: str                  # "2026-06-15"
    day_label: str             # "Mon June 15"
    max_temp_c: float
    min_temp_c: float
    max_rain_prob_pct: float
    max_wind_kmh: float
    dominant_weather: str
    rain_risk: str             # "low" | "medium" | "high"
    wind_risk: str
    heat_risk: str
    overall_risk: str
    hourly: List[HourlySnapshot]


def _classify_risk(rain_prob: float, wind_kmh: float, max_temp: float) -> Dict[str, str]:
    rain = "high" if rain_prob >= 60 else "medium" if rain_prob >= 35 else "low"
    wind = "high" if wind_kmh >= 50 else "medium" if wind_kmh >= 30 else "low"
    heat = "high" if max_temp >= 38 else "medium" if max_temp >= 33 else "low"
    risk_rank = {"low": 0, "medium": 1, "high": 2}
    overall_score = max(risk_rank[rain], risk_rank[wind], risk_rank[heat])
    overall = ["low", "medium", "high"][overall_score]
    return {"rain_risk": rain, "wind_risk": wind, "heat_risk": heat, "overall_risk": overall}


@router.post("/getForecast")
async def get_forecast(req: ForecastRequest) -> Dict[str, Any]:
    """
    Fetch weather forecast from Open-Meteo API.
    Returns structured daily + hourly data with risk classifications.
    Used by Context Agents to get weather context for trip planning.
    """
    params = {
        "latitude": req.latitude,
        "longitude": req.longitude,
        "timezone": req.timezone,
        "hourly": "temperature_2m,precipitation_probability,windspeed_10m,relativehumidity_2m,weathercode",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,windspeed_10m_max,weathercode",
        "forecast_days": 7,
        "wind_speed_unit": "kmh",
    }
    if req.start_date:
        params["start_date"] = req.start_date
        if "forecast_days" in params:
            del params["forecast_days"]
    if req.end_date:
        params["end_date"] = req.end_date
        if "forecast_days" in params:
            del params["forecast_days"]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(OPEN_METEO_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {
            "route": "weather.getForecast",
            "status": "error",
            "errors": [str(e)],
            "output": {},
        }

    daily = data.get("daily", {})
    hourly = data.get("hourly", {})

    daily_forecasts = []
    n_days = len(daily.get("time", []))

    for i in range(n_days):
        date_str = daily["time"][i]
        max_rain = daily["precipitation_probability_max"][i] or 0
        max_wind = daily["windspeed_10m_max"][i] or 0
        max_temp = daily["temperature_2m_max"][i] or 25
        min_temp = daily["temperature_2m_min"][i] or 20
        wmo = daily["weathercode"][i] or 0
        risks = _classify_risk(max_rain, max_wind, max_temp)

        # Collect hourly snapshots for this day
        day_hourly = []
        for h_idx, h_time in enumerate(hourly.get("time", [])):
            if not h_time.startswith(date_str):
                continue
            hour_label = h_time[11:16]  # "08:00"
            h_rain = hourly["precipitation_probability"][h_idx] or 0
            h_wind = hourly["windspeed_10m"][h_idx] or 0
            h_temp = hourly["temperature_2m"][h_idx] or 25
            h_humid = hourly["relativehumidity_2m"][h_idx] or 70
            h_wmo = hourly["weathercode"][h_idx] or 0
            day_hourly.append(HourlySnapshot(
                hour=hour_label,
                temp_c=round(h_temp, 1),
                rain_prob_pct=round(h_rain, 1),
                wind_kmh=round(h_wind, 1),
                humidity_pct=round(h_humid, 1),
                weather_code=h_wmo,
                weather_label=WMO_CODES.get(h_wmo, "Unknown"),
                is_risky=h_rain > 60 or h_wind > 40,
            ))

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        daily_forecasts.append(DailyForecast(
            date=date_str,
            day_label=dt.strftime("%a %b %d"),
            max_temp_c=round(max_temp, 1),
            min_temp_c=round(min_temp, 1),
            max_rain_prob_pct=round(max_rain, 1),
            max_wind_kmh=round(max_wind, 1),
            dominant_weather=WMO_CODES.get(wmo, "Unknown"),
            **risks,
            hourly=day_hourly,
        ).model_dump())

    return {
        "route": "weather.getForecast",
        "context_type": "weather_forecast",
        "status": "success",
        "source": {
            "provider": "open-meteo",
            "freshness": "live",
            "retrieved_at": datetime.now().isoformat(),
        },
        "input": {"latitude": req.latitude, "longitude": req.longitude},
        "output": {
            "daily_forecasts": daily_forecasts,
            "days_count": len(daily_forecasts),
            "timezone": req.timezone,
        },
        "errors": [],
        "warnings": [],
    }
