from pydantic import BaseModel, Field
from datetime import datetime

class WeatherMetrics(BaseModel):
    temperature_c: float
    rain_probability: float = Field(..., ge=0.0, le=100.0)
    wind_speed_kmh: float

class WeatheriseResponseSchema(BaseModel):
    destination_id: str
    location: str
    lat: float
    lon: float
    forecast_time: datetime
    source: str
    metrics: WeatherMetrics