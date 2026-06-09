"""
MCP Route: domain.getExternalRiskData
Returns domain-specific risk data (stub with expandable structure).
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()


class DomainRiskRequest(BaseModel):
    domain: str
    location: Optional[str] = None
    intent: Optional[str] = None


CONSTRUCTION_THRESHOLDS = {
    "concrete_pouring": {
        "max_rain_probability": 20,
        "min_temp_c": 10,
        "max_temp_c": 35,
        "max_wind_kmh": 30,
        "max_humidity_pct": 85,
        "notes": "Concrete curing is impaired by rain, extreme heat, or low humidity.",
    },
    "crane_operation": {
        "max_wind_kmh": 45,
        "max_gust_kmh": 60,
        "notes": "Cranes must be grounded when wind speed exceeds 45 km/h.",
    },
    "general": {
        "max_rain_probability": 40,
        "max_wind_kmh": 50,
        "notes": "General outdoor construction safety thresholds.",
    }
}

AGRICULTURE_THRESHOLDS = {
    "irrigation": {
        "skip_if_rain_probability_above": 60,
        "optimal_temp_range": [20, 32],
        "notes": "Skip irrigation if significant rain is forecast. Irrigate early morning.",
    },
    "harvest": {
        "max_rain_probability": 30,
        "max_wind_kmh": 25,
        "notes": "Harvest windows require dry conditions and manageable wind.",
    },
    "general": {
        "notes": "Monitor humidity for disease risk. High humidity (>80%) favors fungal growth.",
    }
}


@router.post("/getExternalRiskData")
async def get_external_risk_data(req: DomainRiskRequest) -> Dict[str, Any]:
    domain = req.domain.lower()
    intent = (req.intent or "general").lower()

    if domain == "construction":
        key = "general"
        for k in CONSTRUCTION_THRESHOLDS:
            if k in intent:
                key = k
                break
        return {
            "domain": "construction",
            "intent": intent,
            "thresholds": CONSTRUCTION_THRESHOLDS[key],
            "source": "weatherise_rules",
        }

    if domain == "agriculture":
        key = "general"
        for k in AGRICULTURE_THRESHOLDS:
            if k in intent:
                key = k
                break
        return {
            "domain": "agriculture",
            "intent": intent,
            "thresholds": AGRICULTURE_THRESHOLDS[key],
            "source": "weatherise_rules",
        }

    return {"domain": domain, "thresholds": {}, "source": "none"}
