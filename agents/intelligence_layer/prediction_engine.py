"""
Prediction Engine — Deterministic risk scoring on Canonical Weather Data.

This is the reliable backbone. NIM is used for natural language only.
The Prediction Engine decides risk levels. NIM must never override them.

Risk Thresholds:
  Rain probability:  < 30% = low,  30-60% = medium,  > 60% = high
  Temperature:       < 35°C = low, 35-38°C = medium, > 38°C = high
  Wind speed:        < 30 km/h = low, 30-45 km/h = medium, > 45 km/h = high
  Wind (construction): < 20 km/h = low, 20-35 km/h = medium, > 35 km/h = high

Outdoor Suitability:
  Any high risk → poor
  Two+ medium risks → poor
  One medium risk → caution
  All low → good
"""

from typing import Any, Optional
from .schemas import CanonicalWeatherData, PredictionResult, RiskLevel


# ── Scoring Functions ────────────────────────────────────────

def score_rain(probability: Optional[float]) -> RiskLevel:
    """Score rain risk from probability percentage."""
    if probability is None:
        return RiskLevel.medium
    if probability < 30:
        return RiskLevel.low
    if probability <= 60:
        return RiskLevel.medium
    return RiskLevel.high


def score_temperature(temp_c: Optional[float]) -> RiskLevel:
    """Score heat risk from temperature in Celsius."""
    if temp_c is None:
        return RiskLevel.medium
    if temp_c < 35:
        return RiskLevel.low
    if temp_c <= 38:
        return RiskLevel.medium
    return RiskLevel.high


def score_wind(wind_kmh: Optional[float], domain: str = "tourism") -> RiskLevel:
    """Score wind risk. Construction has stricter thresholds."""
    if wind_kmh is None:
        return RiskLevel.medium

    if domain == "construction":
        threshold_medium, threshold_high = 20, 35
    else:
        threshold_medium, threshold_high = 30, 45

    if wind_kmh < threshold_medium:
        return RiskLevel.low
    if wind_kmh <= threshold_high:
        return RiskLevel.medium
    return RiskLevel.high


def combine_trip_risk(*risks: RiskLevel) -> RiskLevel:
    """Combine multiple risk levels into overall trip disruption risk."""
    risk_values = list(risks)
    if RiskLevel.high in risk_values:
        return RiskLevel.high
    if risk_values.count(RiskLevel.medium) >= 2:
        return RiskLevel.high
    if RiskLevel.medium in risk_values:
        return RiskLevel.medium
    return RiskLevel.low


# ── Helper Functions ─────────────────────────────────────────

def max_value(points: list[dict[str, Any]], key: str) -> Optional[float]:
    """Get the maximum value for a given key across all weather points."""
    values = [
        p.get(key) for p in points
        if isinstance(p.get(key), (int, float))
    ]
    return max(values) if values else None


# ── Domain Predictors ────────────────────────────────────────

def predict_tourism(
    processed_json: dict[str, Any],
    canonical_weather: CanonicalWeatherData,
) -> PredictionResult:
    """Tourism domain prediction with rain, heat, wind, and trip disruption risk."""
    points = [v.model_dump() for v in canonical_weather.variables]

    max_rain = max_value(points, "rain_probability")
    max_temp = max_value(points, "temperature_c")
    max_wind = max_value(points, "wind_speed_kmh")

    rain_risk = score_rain(max_rain)
    heat_risk = score_temperature(max_temp)
    wind_risk = score_wind(max_wind, domain="tourism")
    trip_risk = combine_trip_risk(rain_risk, heat_risk, wind_risk)

    return PredictionResult(
        domain="tourism",
        prediction_summary=(
            f"Rain risk is {rain_risk.value}, heat risk is {heat_risk.value}, "
            f"and wind risk is {wind_risk.value}."
        ),
        recommendation_summary=(
            "Adjust outdoor activities based on the highest weather risk "
            "and keep suitable indoor backups."
        ),
        risk_assessment={
            "rain_risk": rain_risk,
            "heat_risk": heat_risk,
            "wind_risk": wind_risk,
            "trip_disruption_risk": trip_risk,
        },
        evidence=[
            f"Maximum rain probability: {max_rain}%",
            f"Maximum temperature: {max_temp}°C",
            f"Maximum wind speed: {max_wind} km/h",
        ],
    )


def predict_construction(
    processed_json: dict[str, Any],
    canonical_weather: CanonicalWeatherData,
) -> PredictionResult:
    """Construction domain prediction with stricter wind thresholds."""
    points = [v.model_dump() for v in canonical_weather.variables]

    max_rain = max_value(points, "rain_probability")
    max_temp = max_value(points, "temperature_c")
    max_wind = max_value(points, "wind_speed_kmh")

    rain_risk = score_rain(max_rain)
    heat_risk = score_temperature(max_temp)
    wind_risk = score_wind(max_wind, domain="construction")
    overall_risk = combine_trip_risk(rain_risk, heat_risk, wind_risk)

    return PredictionResult(
        domain="construction",
        prediction_summary=(
            f"Rain risk is {rain_risk.value}, heat risk is {heat_risk.value}, "
            f"and wind risk is {wind_risk.value} for construction operations."
        ),
        recommendation_summary=(
            "Pause outdoor operations during high-risk periods. "
            "Check wind gust thresholds before crane operations."
        ),
        risk_assessment={
            "rain_risk": rain_risk,
            "heat_risk": heat_risk,
            "wind_risk": wind_risk,
            "construction_safety_risk": overall_risk,
        },
        evidence=[
            f"Maximum rain probability: {max_rain}%",
            f"Maximum temperature: {max_temp}°C",
            f"Maximum wind speed: {max_wind} km/h",
        ],
    )


def predict_agriculture(
    processed_json: dict[str, Any],
    canonical_weather: CanonicalWeatherData,
) -> PredictionResult:
    """Agriculture domain prediction for irrigation, disease, and harvest timing."""
    points = [v.model_dump() for v in canonical_weather.variables]

    max_rain = max_value(points, "rain_probability")
    max_temp = max_value(points, "temperature_c")
    max_humidity = max_value(points, "humidity_percent")

    rain_risk = score_rain(max_rain)
    heat_risk = score_temperature(max_temp)

    # Agriculture-specific: disease risk from humidity + temperature
    disease_risk = RiskLevel.low
    if max_humidity and max_temp:
        if max_humidity > 80 and 25 <= max_temp <= 35:
            disease_risk = RiskLevel.high
        elif max_humidity > 70:
            disease_risk = RiskLevel.medium

    return PredictionResult(
        domain="agriculture",
        prediction_summary=(
            f"Rain risk is {rain_risk.value}, heat risk is {heat_risk.value}, "
            f"and crop disease risk is {disease_risk.value}."
        ),
        recommendation_summary=(
            "Delay irrigation if heavy rain is expected. "
            "Monitor humidity levels for disease risk."
        ),
        risk_assessment={
            "rain_risk": rain_risk,
            "heat_risk": heat_risk,
            "disease_risk": disease_risk,
        },
        evidence=[
            f"Maximum rain probability: {max_rain}%",
            f"Maximum temperature: {max_temp}°C",
            f"Maximum humidity: {max_humidity}%",
        ],
    )


# ── Main Entry Point ─────────────────────────────────────────

class PredictionEngine:
    """
    Deterministic prediction engine.
    Routes by domain, scores risk from canonical weather data.
    """

    PREDICTORS = {
        "tourism": predict_tourism,
        "construction": predict_construction,
        "agriculture": predict_agriculture,
    }

    def predict(
        self,
        processed_json: Any,
        canonical_weather: CanonicalWeatherData,
    ) -> PredictionResult:
        """
        Run domain-specific prediction on canonical weather data.

        Args:
            processed_json: FullyProcessedJSON or dict with at least 'domain'
            canonical_weather: Normalized weather data

        Returns:
            PredictionResult with deterministic risk assessment.
        """
        if hasattr(processed_json, "model_dump"):
            pj_dict = processed_json.model_dump()
        elif isinstance(processed_json, dict):
            pj_dict = processed_json
        else:
            pj_dict = {"domain": "tourism"}

        domain = pj_dict.get("domain", "tourism")
        predictor = self.PREDICTORS.get(domain, predict_tourism)
        return predictor(pj_dict, canonical_weather)
