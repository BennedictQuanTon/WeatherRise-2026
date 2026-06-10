"""
Weatherise Intelligence Layer — Schemas

Self-contained Pydantic models for the entire Intelligence Layer.
No imports from apps.api — the Intelligence Layer owns its own contracts.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ── Input Contract ───────────────────────────────────────────

class Coordinates(BaseModel):
    latitude: float
    longitude: float


class GeographicalLocation(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    coordinates: Coordinates


class TimeRange(BaseModel):
    raw_text: Optional[str] = None
    start: str
    end: str
    timezone: str = "Asia/Ho_Chi_Minh"


class IntelligenceRequirements(BaseModel):
    realtime_weather_needed: bool = True
    weather_variables: list[str] = Field(default_factory=list)
    reasoning_task: str


class FullyProcessedJSON(BaseModel):
    """Complete input contract from Context Agent → Intelligence Layer."""
    domain: str
    intent: str
    location: Optional[str] = None
    geographical_location: GeographicalLocation
    time_range: TimeRange
    involved_context: list[str] = Field(default_factory=list)
    knowledge_context: dict[str, Any] = Field(default_factory=dict)
    mcp_context: dict[str, Any] = Field(default_factory=dict)
    intelligence_requirements: IntelligenceRequirements
    user_constraints: list[str] = Field(default_factory=list)
    raw_user_input: Optional[str] = None


# ── Canonical Weather Schema ─────────────────────────────────

class CanonicalWeatherPoint(BaseModel):
    """Single hourly weather data point in normalized format."""
    time: str
    temperature_c: Optional[float] = None
    rain_probability: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    humidity_percent: Optional[float] = None
    weather_code: Optional[int] = None
    storm_risk: Optional[str] = None


class CanonicalWeatherData(BaseModel):
    """
    Stable internal weather schema.
    All weather sources must be converted into this format
    before the Prediction Engine sees them.
    """
    source: str
    source_type: str
    location: dict[str, Any]
    forecast_window: dict[str, str]
    resolution: dict[str, str]
    variables: list[CanonicalWeatherPoint]
    data_quality: dict[str, Any]


# ── Prediction Engine Output ─────────────────────────────────

class PredictionResult(BaseModel):
    """Deterministic risk scoring output from the Prediction Engine."""
    domain: str
    prediction_summary: str
    recommendation_summary: str
    risk_assessment: dict[str, RiskLevel]
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── NIM Response ─────────────────────────────────────────────

class NIMResponse(BaseModel):
    """Structured response from the NIM LLM endpoint."""
    model: str
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    error: Optional[str] = None


# ── Final Output Contract ────────────────────────────────────

class IntelligenceOutput(BaseModel):
    """
    Final Intelligence Layer output contract.
    risk_assessment always comes from PredictionEngine, never from NIM.
    """
    prediction: str
    recommendation: str
    risk_assessment: dict[str, RiskLevel]
    explanation: str
    final_answer: str
    metadata: dict[str, Any] = Field(default_factory=dict)
