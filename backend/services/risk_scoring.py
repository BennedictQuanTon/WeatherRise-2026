from backend.schemas.weather_schema import WeatherSchema

class RiskScoringService:
    def evaluate(self, weather: WeatherSchema) -> dict:
        # Rain Risk
        rain_prob = weather.precipitation_probability
        if rain_prob < 30:
            rain_risk = "low"
        elif 30 <= rain_prob <= 60:
            rain_risk = "medium"
        else:
            rain_risk = "high"

        # Heat Risk
        temp = weather.temperature_c
        if temp < 35:
            heat_risk = "low"
        elif 35 <= temp <= 38:
            heat_risk = "medium"
        else:
            heat_risk = "high"

        # Wind Risk
        wind = weather.wind_speed_kmh
        if wind < 30:
            wind_risk = "low"
        elif 30 <= wind <= 45:
            wind_risk = "medium"
        else:
            wind_risk = "high"

        # Overall Outdoor Suitability
        risks = [rain_risk, heat_risk, wind_risk]
        if "high" in risks:
            overall = "poor"
        elif risks.count("medium") >= 2:
            overall = "poor"
        elif risks.count("medium") == 1:
            overall = "caution"
        else:
            overall = "good"

        return {
            "rain": rain_risk,
            "heat": heat_risk,
            "wind": wind_risk,
            "overall": overall
        }

risk_scoring = RiskScoringService()
