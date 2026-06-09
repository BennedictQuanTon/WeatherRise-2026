from pydantic import BaseModel
from typing import Optional

class WeatherSchema(BaseModel):
    temperature_c: float
    wind_speed_kmh: float
    precipitation_probability: int
    weather_condition: str
    is_fallback: bool = False
    source: str = "open_meteo"
