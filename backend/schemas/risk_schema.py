from pydantic import BaseModel
from typing import Dict, Any

class RiskScore(BaseModel):
    rain: str
    heat: str
    wind: str
    overall: str

class WeatheriseRiskSchema(BaseModel):
    destination_id: str
    location: str
    risk: RiskScore
    impact: str
    recommendation: str
    monitoring_enabled: bool
    raw_weather: Dict[str, Any] = {}
