import os
import httpx
from typing import Optional

class OpenWeatherClient:
    """Defensive current weather conditions fallback interface layer."""
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        self.endpoint = "https://api.openweathermap.org/data/2.5/weather"

    async def fetch_current_fallback(self, lat: float, lon: float) -> Optional[dict]:
        if not self.api_key or "your-key" in self.api_key or not self.api_key.strip():
            # Graceful extraction avoidance if credentials are not configured
            return None
        
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                res = await client.get(self.endpoint, params=params)
                return res.json() if res.status_code == 200 else None
            except httpx.RequestError:
                return None