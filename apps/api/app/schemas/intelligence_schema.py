from pydantic import BaseModel
from typing import Optional, Dict


class RiskAssessment(BaseModel):
    rain_risk: str = "unknown"
    wind_risk: str = "unknown"
    heat_risk: str = "unknown"
    overall_risk: str = "unknown"
    trip_disruption_risk: Optional[str] = None


class IntelligenceOutput(BaseModel):
    prediction: str
    recommendation: str
    risk_assessment: RiskAssessment
    explanation: str
    final_answer: str
    domain: str
    location: Optional[str] = None
    time_range: Optional[Dict] = None
