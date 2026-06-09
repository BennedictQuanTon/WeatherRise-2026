from fastapi import APIRouter
from backend.schemas.request_schema import WeatherAnalyzeRequest
from backend.schemas.risk_schema import WeatheriseRiskSchema
from backend.agents.orchestrator_agent import orchestrator

from backend.schemas.response_schema import StandardResponse, success_response, error_response
import datetime

router = APIRouter(prefix="/weather", tags=["Weather Intelligence"])

@router.post("/analyze", response_model=StandardResponse)
async def analyze_weather(req: WeatherAnalyzeRequest):
    try:
        result = orchestrator.process_request(req)
        return success_response(data=result.model_dump(), meta={"source": "open_meteo/nemotron", "timestamp": datetime.datetime.now().isoformat()})
    except Exception as e:
        return error_response(code="weather_analysis_failed", message=str(e))
