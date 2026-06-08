import httpx
from fastapi import HTTPException

class OpenMeteoClient:
    """Async wrapper managing HTTPX connection sessions targeting Open-Meteo."""
    def __init__(self):
        self.endpoint = "https://api.open-meteo.com/v1/forecast"

    async def get_hourly_timeline(self, lat: float, lon: float) -> dict:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation_probability,wind_speed_10m",
            "timezone": "Asia/Ho_Chi_Minh",
            "forecast_days": 7
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.endpoint, params=params)
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail="Upstream Open-Meteo failure response.")
                return response.json()
            except httpx.RequestError as exc:
                raise HTTPException(status_code=504, detail=f"Network connection timeout: {exc}")