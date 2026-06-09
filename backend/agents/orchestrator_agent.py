import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage
from backend.agents.weather_agent import weather_agent
from backend.schemas.request_schema import WeatherAnalyzeRequest
from backend.schemas.risk_schema import WeatheriseRiskSchema
import json

class OrchestratorAgent:
    def __init__(self):
        base_url = os.getenv("NVIDIA_BASE_URL", "http://localhost:8001/v1")
        api_key = os.getenv("NVIDIA_API_KEY", "local")
        
        self.llm = ChatNVIDIA(
            base_url=base_url, 
            api_key=api_key,
            model="meta/llama3-8b-instruct" # Standard alias for NIM testing
        )

    def process_request(self, req: WeatherAnalyzeRequest) -> WeatheriseRiskSchema:
        # Step 1: Call Weather Agent to get data and base risks
        risk_schema = weather_agent.get_weather_risk(
            req.destination_id, 
            req.forecast_date, 
            req.forecast_time
        )
        risk_schema.monitoring_enabled = req.monitoring_enabled
        
        # Step 2: Use LLM to generate a more human-like impact and recommendation
        prompt = f"""
        You are Weatherise, an expert travel weather assistant in Da Nang.
        The user wants to visit '{risk_schema.location}'.
        Weather data: Temp {risk_schema.raw_weather.get('temperature_c')}C, Wind {risk_schema.raw_weather.get('wind_speed_kmh')}km/h, Rain {risk_schema.raw_weather.get('precipitation_probability')}%.
        Risk levels: Rain ({risk_schema.risk.rain}), Heat ({risk_schema.risk.heat}), Wind ({risk_schema.risk.wind}), Overall ({risk_schema.risk.overall}).
        
        Write a short 1-sentence impact statement, and a short 1-sentence recommendation.
        Format output strictly as JSON with keys: "impact", "recommendation".
        """
        
        try:
            res = self.llm.invoke([HumanMessage(content=prompt)])
            content = res.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            if "impact" in data:
                risk_schema.impact = data["impact"]
            if "recommendation" in data:
                risk_schema.recommendation = data["recommendation"]
        except Exception as e:
            print(f"LLM Generation failed: {e}. Using fallback texts.")
            
        return risk_schema

orchestrator = OrchestratorAgent()
