"""
Rule-based prediction engine for weather risk scoring.
Deterministic, fast, explainable — keeps demo reliable.
"""
from typing import Dict, Any, Optional
from apps.api.app.schemas.intelligence_schema import RiskAssessment


class PredictionEngine:
    """
    Evaluates weather variables and domain context into risk scores.
    Rules are intentionally simple and explainable for hackathon demo.
    """

    # Risk thresholds
    RAIN_LOW = 30
    RAIN_HIGH = 60
    TEMP_HEAT_MEDIUM = 35
    TEMP_HEAT_HIGH = 38
    WIND_MEDIUM = 30
    WIND_HIGH = 45

    def evaluate(self, weather: Dict[str, Any], domain: str) -> RiskAssessment:
        rain = weather.get("rain_probability", 0)
        temp = weather.get("temperature", 28)
        wind = weather.get("wind_speed", 10)

        rain_risk = self._rain_risk(rain)
        heat_risk = self._heat_risk(temp)
        wind_risk = self._wind_risk(wind, domain)
        overall = self._overall_risk(rain_risk, heat_risk, wind_risk)

        trip_disruption = None
        if domain == "tourism":
            trip_disruption = "high" if rain_risk == "high" or wind_risk == "high" else (
                "medium" if rain_risk == "medium" else "low"
            )

        return RiskAssessment(
            rain_risk=rain_risk,
            heat_risk=heat_risk,
            wind_risk=wind_risk,
            overall_risk=overall,
            trip_disruption_risk=trip_disruption,
        )

    def _rain_risk(self, prob: float) -> str:
        if prob < self.RAIN_LOW:
            return "low"
        elif prob <= self.RAIN_HIGH:
            return "medium"
        return "high"

    def _heat_risk(self, temp: float) -> str:
        if temp < self.TEMP_HEAT_MEDIUM:
            return "low"
        elif temp <= self.TEMP_HEAT_HIGH:
            return "medium"
        return "high"

    def _wind_risk(self, wind: float, domain: str) -> str:
        # Crane operations are more sensitive to wind
        threshold_medium = 20 if domain == "construction" else self.WIND_MEDIUM
        threshold_high = 35 if domain == "construction" else self.WIND_HIGH
        if wind < threshold_medium:
            return "low"
        elif wind <= threshold_high:
            return "medium"
        return "high"

    def _overall_risk(self, rain: str, heat: str, wind: str) -> str:
        risks = [rain, heat, wind]
        if "high" in risks:
            return "poor"
        if risks.count("medium") >= 2:
            return "poor"
        if "medium" in risks:
            return "caution"
        return "good"
