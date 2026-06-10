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


class TripRequest(BaseModel):
    duration_days: Optional[int] = None
    trip_style: str = "general"
    pace: str = "balanced"
    preferences: List[str] = Field(default_factory=list)
    include_restaurants: bool = True
    include_routes: bool = True
    include_indoor_backups: bool = True
    weather_aware: bool = True


class ParserOutput(BaseModel):
    domain: str
    intent: str
    intent_subtype: Optional[str] = None  # 'multi_day_trip_planning' | None
    location: Optional[str] = None
    geographical_location: GeographicalLocation = Field(default_factory=GeographicalLocation)
    time_range: TimeRange = Field(default_factory=TimeRange)
    trip_request: Optional[TripRequest] = None  # V3: filled when intent_subtype is trip
    involved_context: List[str] = Field(default_factory=list)
    user_constraints: List[str] = Field(default_factory=list)
    raw_user_input: str


# ── Context Agent Intermediate ───────────────────────────────
class KnowledgeContext(BaseModel):
    found_context: Dict[str, Any] = Field(default_factory=dict)
    missing_context: List[str] = Field(default_factory=list)


class MCPContext(BaseModel):
    coordinates: Optional[Dict[str, float]] = None
    weather_forecast: Optional[Dict[str, Any]] = None
    realtime_weather: Optional[Dict[str, Any]] = None
    places: Optional[List[Dict[str, Any]]] = None
    restaurants: Optional[List[Dict[str, Any]]] = None
    opening_hours: Optional[Dict[str, Any]] = None
    distance_matrix: Optional[Dict[str, Any]] = None
    trip_plan_context: Optional[Dict[str, Any]] = None
    time_range_resolved: Optional[Dict[str, str]] = None
    external_risk_data: Optional[Dict[str, Any]] = None


class IntelligenceRequirements(BaseModel):
    realtime_weather_needed: bool = True
    weather_variables: List[str] = Field(default_factory=list)
    reasoning_task: str = "general_weather_advice"


# ── V3 Fully Processed Payload ───────────────────────────────
class ContextStatus(BaseModel):
    knowledge_base_complete: bool = False
    mcp_called: bool = False
    missing_context_resolved: bool = True
    context_quality: str = "usable_for_prediction"
    # 'complete' | 'usable_for_trip_planning' | 'usable_for_prediction' | 'partial' | 'blocked'
    trip_plan_ready: bool = False
    weather_optimization_ready: bool = False
    weather_optimization_reason: Optional[str] = None


class FullyProcessedPayload(BaseModel):
    """V3 fully processed payload sent to Intelligence Layer."""
    domain: str
    intent: str
    intent_subtype: Optional[str] = None
    location: Optional[str] = None
    geographical_location: GeographicalLocation = Field(default_factory=GeographicalLocation)
    time_range: TimeRange = Field(default_factory=TimeRange)
    trip_request: Optional[TripRequest] = None
    involved_context: List[str] = Field(default_factory=list)
    knowledge_context: KnowledgeContext = Field(default_factory=KnowledgeContext)
    mcp_context: MCPContext = Field(default_factory=MCPContext)
    context_status: ContextStatus = Field(default_factory=ContextStatus)
    intelligence_requirements: IntelligenceRequirements = Field(default_factory=IntelligenceRequirements)
    user_constraints: List[str] = Field(default_factory=list)
    raw_user_input: str = ""
