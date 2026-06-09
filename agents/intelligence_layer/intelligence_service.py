"""
Intelligence Service
Receives a FullyProcessedPayload and produces the final weather-aware advice using:
  1. Rule-based risk scoring (prediction_engine)
  2. NVIDIA NIM LLM for natural language explanation and recommendation
"""
import json
from agents.intelligence_layer.nim_client import NIMClient
from agents.intelligence_layer.prediction_engine import PredictionEngine
from apps.api.app.schemas.context_schema import FullyProcessedPayload
from apps.api.app.schemas.intelligence_schema import IntelligenceOutput, RiskAssessment

INTELLIGENCE_SYSTEM_PROMPT = """You are Weatherise, an expert weather-risk intelligence system.
You receive structured JSON with weather data, domain context, and user constraints.
Your job is to produce a clear, helpful, and accurate weather-risk analysis.

RULES:
1. Be specific with times, dates, and weather values when available.
2. Always acknowledge the user's constraints (e.g., "you want to avoid heavy rain").
3. Give concrete recommendations (e.g., "visit Ba Na Hills in the morning", not "plan carefully").
4. Use the risk assessment provided. Do NOT make up weather data.
5. Keep the final_answer concise and user-friendly (3-5 sentences).
6. Speak directly to the user. Use "you" and "your".

OUTPUT FORMAT (valid JSON only):
{
  "prediction": "<1-2 sentence weather prediction>",
  "recommendation": "<concrete action recommendation>",
  "explanation": "<brief explanation of why this advice is given>",
  "final_answer": "<concise, user-friendly summary answer>"
}"""


class IntelligenceService:
    def __init__(self):
        self.nim = NIMClient()
        self.engine = PredictionEngine()

    async def reason(self, payload: FullyProcessedPayload) -> IntelligenceOutput:
        """Generate final weather advice from fully processed context."""

        # Extract weather data from MCP context
        weather_data = {}
        if payload.mcp_context.weather_forecast:
            forecast = payload.mcp_context.weather_forecast
            # Use first day's data as representative
            daily = forecast.get("daily", {})
            hourly = forecast.get("hourly", {})
            weather_data = {
                "rain_probability": (daily.get("precipitation_probability_max", [50])[0]
                                     if daily.get("precipitation_probability_max") else
                                     hourly.get("precipitation_probability", [50])[0] if hourly else 50),
                "temperature": (daily.get("temperature_2m_max", [30])[0]
                                if daily.get("temperature_2m_max") else
                                hourly.get("temperature_2m", [30])[0] if hourly else 30),
                "wind_speed": (daily.get("wind_speed_10m_max", [15])[0]
                               if daily.get("wind_speed_10m_max") else
                               hourly.get("wind_speed_10m", [15])[0] if hourly else 15),
                "humidity": hourly.get("relative_humidity_2m", [70])[0] if hourly else 70,
            }

        # Rule-based risk assessment
        risk = self.engine.evaluate(weather_data, payload.domain)

        # Build context summary for NIM
        context_summary = {
            "domain": payload.domain,
            "intent": payload.intent,
            "location": payload.location,
            "time_range": payload.time_range.model_dump() if payload.time_range else {},
            "weather_data": weather_data,
            "risk_assessment": {
                "rain_risk": risk.rain_risk,
                "heat_risk": risk.heat_risk,
                "wind_risk": risk.wind_risk,
                "overall_risk": risk.overall_risk,
                "trip_disruption_risk": risk.trip_disruption_risk,
            },
            "user_constraints": payload.user_constraints,
            "involved_context": payload.involved_context,
            "places": payload.mcp_context.places[:5] if payload.mcp_context.places else [],
        }

        user_prompt = f"Weather intelligence context:\n{json.dumps(context_summary, indent=2, ensure_ascii=False)}"

        try:
            nim_response = await self.nim.complete(
                system_prompt=INTELLIGENCE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,
            )

            # Parse JSON response
            import re
            json_match = re.search(r"\{.*\}", nim_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}

            return IntelligenceOutput(
                prediction=data.get("prediction", f"Weather risk is {risk.overall_risk} for {payload.domain} activities."),
                recommendation=data.get("recommendation", self._fallback_recommendation(risk, payload.domain)),
                risk_assessment=risk,
                explanation=data.get("explanation", f"Based on rain risk ({risk.rain_risk}), heat risk ({risk.heat_risk}), and wind risk ({risk.wind_risk})."),
                final_answer=data.get("final_answer", f"Overall conditions are {risk.overall_risk} for your {payload.domain} plans."),
                domain=payload.domain,
                location=payload.location,
                time_range=payload.time_range.model_dump() if payload.time_range else None,
            )

        except Exception as e:
            print(f"[Intelligence] NIM error: {e}, using fallback")
            return IntelligenceOutput(
                prediction=f"Weather conditions are {risk.overall_risk} for {payload.domain} activities.",
                recommendation=self._fallback_recommendation(risk, payload.domain),
                risk_assessment=risk,
                explanation=f"Rain risk: {risk.rain_risk}, Heat risk: {risk.heat_risk}, Wind risk: {risk.wind_risk}.",
                final_answer=f"Based on current weather data, conditions are {risk.overall_risk} for your plans in {payload.location or 'the area'}.",
                domain=payload.domain,
                location=payload.location,
            )

    def _fallback_recommendation(self, risk: RiskAssessment, domain: str) -> str:
        if risk.overall_risk == "good":
            return "Conditions look good. Proceed with your plans."
        elif risk.overall_risk == "caution":
            return "Exercise caution. Monitor weather updates before proceeding."
        else:
            if domain == "tourism":
                return "Consider indoor alternatives or reschedule outdoor activities."
            elif domain == "construction":
                return "Pause outdoor operations until conditions improve."
            elif domain == "agriculture":
                return "Delay field operations. Monitor rainfall before irrigation decisions."
            return "Conditions are poor. Postpone outdoor activities."
