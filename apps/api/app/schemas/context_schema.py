from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ── Parser Output ────────────────────────────────────────────
class GeographicalLocation(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None


class TimeRange(BaseModel):
    raw_text: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    timezone: str = "Asia/Ho_Chi_Minh"


class ParserOutput(BaseModel):
    domain: str  # tourism | construction | agriculture | unknown
    intent: str
    location: Optional[str] = None
    geographical_location: GeographicalLocation = Field(default_factory=GeographicalLocation)
    time_range: TimeRange = Field(default_factory=TimeRange)
    involved_context: List[str] = Field(default_factory=list)
    user_constraints: List[str] = Field(default_factory=list)
    raw_user_input: str


# ── Context Agent Output ─────────────────────────────────────
class KnowledgeContext(BaseModel):
    found_context: Dict[str, Any] = Field(default_factory=dict)
    missing_context: List[str] = Field(default_factory=list)


class MCPContext(BaseModel):
    coordinates: Optional[Dict[str, float]] = None
    weather_forecast: Optional[Dict[str, Any]] = None
    realtime_weather: Optional[Dict[str, Any]] = None
    places: Optional[List[Dict[str, Any]]] = None
    opening_hours: Optional[Dict[str, Any]] = None
    time_range_resolved: Optional[Dict[str, str]] = None
    external_risk_data: Optional[Dict[str, Any]] = None


class IntelligenceRequirements(BaseModel):
    realtime_weather_needed: bool = True
    weather_variables: List[str] = Field(default_factory=list)
    reasoning_task: str = "general_weather_advice"


class FullyProcessedPayload(BaseModel):
    domain: str
    intent: str
    location: Optional[str] = None
    geographical_location: GeographicalLocation = Field(default_factory=GeographicalLocation)
    time_range: TimeRange = Field(default_factory=TimeRange)
    involved_context: List[str] = Field(default_factory=list)
    knowledge_context: KnowledgeContext = Field(default_factory=KnowledgeContext)
    mcp_context: MCPContext = Field(default_factory=MCPContext)
    intelligence_requirements: IntelligenceRequirements = Field(default_factory=IntelligenceRequirements)
    user_constraints: List[str] = Field(default_factory=list)
    raw_user_input: str = ""
