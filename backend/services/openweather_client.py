import requests
import os
from typing import Optional
from backend.schemas.weather_schema import WeatherSchema
from dotenv import load_dotenv

load_dotenv()

class OpenWeatherClient:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    def get_current_weather(self, lat: float, lon: float) -> Optional[WeatherSchema]:
        """
        Fallback to get current weather if forecast fails.
        """
        if not self.api_key:
            print("OpenWeatherMap API Key is missing.")
            return None
            
        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            temp = data.get("main", {}).get("temp", 0.0)
            wind = data.get("wind", {}).get("speed", 0.0) * 3.6 # convert m/s to km/h
            
            # OWM doesn't give precip probability for current weather easily
            weather_desc = data.get("weather", [{}])[0].get("main", "Clear")
            precip = 80 if weather_desc in ["Rain", "Thunderstorm", "Drizzle"] else 0
            
            return WeatherSchema(
                temperature_c=temp,
                wind_speed_kmh=round(wind, 1),
                precipitation_probability=precip,
                weather_condition=weather_desc,
                is_fallback=True,
                source="openweathermap"
            )
        except Exception as e:
            print(f"OpenWeatherMap Error: {e}")
            return None
