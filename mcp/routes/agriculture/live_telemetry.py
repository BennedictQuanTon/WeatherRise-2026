"""
MCP Route: agriculture.getLiveTelemetry
Real-time specialized Open-Meteo Agrometeorology data.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import logging

router = APIRouter()
logger = logging.getLogger("mcp_agriculture_telemetry")

class AgricultureTelemetryRequest(BaseModel):
    intent: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

@router.post("/getLiveTelemetry")
async def get_live_telemetry(req: AgricultureTelemetryRequest) -> Dict[str, Any]:
    intent = (req.intent or "general").lower()
    latitude = req.lat if req.lat is not None else 16.0471
    longitude = req.lon if req.lon is not None else 108.2062

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Query specialized agro endpoint for soil tensors and evapotranspiration
            api_endpoint = "https://agrometeorology-api.open-meteo.com/v1/agrometeorology"
            
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": ["soil_moisture_0_to_10cm", "soil_temperature_0_to_10cm", "evapotranspiration"],
                "timezone": "Asia/Ho_Chi_Minh"
            }
            
            response = await client.get(api_endpoint, params=params)
            response.raise_for_status()
            agro_data = response.json()
            
            current_agro = agro_data.get("current", {})
            
            # Dynamically scale thresholds based on real-time soil saturation conditions
            soil_moisture = current_agro.get("soil_moisture_0_to_10cm", 0.3)
            evapotranspiration = current_agro.get("evapotranspiration", 0.2)
            
            # Analytical Rule Calculation: High initial soil moisture drops acceptable rain limits
            calculated_rain_skip = 60 if soil_moisture < 0.4 else 30
            
            return {
                "domain": "agriculture",
                "intent": intent,
                "source": "open_meteo_agrometeorology_live",
                "live_telemetry": {
                    "soil_moisture_m3_m3": soil_moisture,
                    "soil_temperature_c": current_agro.get("soil_temperature_0_to_10cm"),
                    "evapotranspiration_mm": evapotranspiration
                },
                "thresholds": {
                    "skip_if_rain_probability_above": calculated_rain_skip,
                    "optimal_temp_range": [20, 32],
                    "max_wind_kmh_threshold": 15.0 if "spray" in intent or "pest" in intent else 25.0,
                    "critical_dry_time_hours": 6 if evapotranspiration < 0.5 else 3
                }
            }
        except Exception as e:
            logger.error(f"Upstream Agriculture API Failure: {e}")
            # Fallback on failure: do not hallucinate, return blank.
            return {
                "domain": "agriculture", 
                "intent": intent, 
                "source": "open_meteo_failed", 
                "thresholds": {}
            }
