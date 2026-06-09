import requests
from typing import Optional
from backend.schemas.weather_schema import WeatherSchema

class OpenMeteoClient:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, lat: float, lon: float, date_str: str, time_str: str) -> Optional[WeatherSchema]:
        """
        Get weather forecast for a specific location, date and time.
        date_str format: YYYY-MM-DD
        time_str format: HH:MM
        """
        try:
            # We fetch hourly data
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
                "timezone": "Asia/Ho_Chi_Minh",
                "start_date": date_str,
                "end_date": date_str
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find the specific hour index
            target_time = f"{date_str}T{time_str}"
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            try:
                # Open-Meteo returns time like "2026-06-08T18:00"
                target_prefix = f"{date_str}T{time_str.split(':')[0]}:00"
                idx = times.index(target_prefix)
            except ValueError:
                idx = 0 # Fallback to first hour of the day if time mismatch
                
            temp = hourly.get("temperature_2m", [])[idx]
            precip = hourly.get("precipitation_probability", [])[idx]
            wind = hourly.get("wind_speed_10m", [])[idx]
            wcode = hourly.get("weather_code", [])[idx]
            
            # Simplified WMO weather code mapping to string condition
            condition = "Clear" if wcode <= 3 else "Cloudy"
            if wcode >= 51 and wcode <= 69: condition = "Rain"
            if wcode >= 71 and wcode <= 79: condition = "Snow"
            if wcode >= 80: condition = "Heavy Rain/Storm"
            
            return WeatherSchema(
                temperature_c=temp,
                wind_speed_kmh=wind,
                precipitation_probability=precip,
                weather_condition=condition,
                is_fallback=False,
                source="open_meteo"
            )
        except Exception as e:
            print(f"Open-Meteo Error: {e}")
            return None
