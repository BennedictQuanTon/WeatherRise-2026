from backend.services.open_meteo_client import OpenMeteoClient
from backend.services.openweather_client import OpenWeatherClient
from backend.services.risk_scoring import risk_scoring
from backend.services.destination_service import destination_service
from backend.schemas.risk_schema import WeatheriseRiskSchema, RiskScore

class WeatherAgent:
    def __init__(self):
        self.meteo = OpenMeteoClient()
        self.owm = OpenWeatherClient()

    def get_weather_risk(self, destination_id: str, date_str: str, time_str: str) -> WeatheriseRiskSchema:
        dest = destination_service.get_by_id(destination_id)
        if not dest:
            raise ValueError("Destination not found")

        # Try Meteo forecast first
        weather = self.meteo.get_forecast(dest.lat, dest.lon, date_str, time_str)
        
        # Fallback to OWM current weather
        if not weather:
            weather = self.owm.get_current_weather(dest.lat, dest.lon)
            
        if not weather:
            raise Exception("Weather services unavailable")

        # Risk scoring
        risk_dict = risk_scoring.evaluate(weather)
        risk = RiskScore(**risk_dict)
        
        # Basic impact/recommendation generation (This can be powered by LLM in Orchestrator)
        impact = "Weather conditions are stable."
        rec = "Proceed with your planned activity."
        
        if risk.overall == "poor":
            impact = f"High risks detected for this {dest.activity_type.replace('_', ' ')}."
            if dest.safe_alternatives:
                rec = f"Consider safer alternatives like {', '.join(dest.safe_alternatives)}."
            else:
                rec = "Consider rescheduling."
        elif risk.overall == "caution":
            impact = "Moderate risks detected. Be prepared."
            rec = "Proceed with caution, monitor updates."

        return WeatheriseRiskSchema(
            destination_id=destination_id,
            location=dest.name,
            risk=risk,
            impact=impact,
            recommendation=rec,
            monitoring_enabled=True,
            raw_weather=weather.model_dump()
        )

weather_agent = WeatherAgent()
