from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class TripStop(BaseModel):
    order: int
    place_id: str
    name: str
    lat: float
    lon: float
    time_block: str  # 'morning' | 'lunch' | 'afternoon' | 'dinner' | 'evening'
    planned_time: str  # "08:00"
    forecast_temp: Optional[float] = None
    weather_condition: Optional[str] = None
    duration_minutes: int = 60
    is_indoor: bool = False
    category: str = "attraction"
    vibe_tags: List[str] = []
    backup_for: Optional[str] = None  # place_id it replaces if weather bad


class TripDay(BaseModel):
    day: int
    theme: Optional[str] = None
    primary_area: Optional[str] = None
    stops: List[TripStop] = []
    backup_options: List[Dict[str, Any]] = []
    date: Optional[str] = None
    weather_condition: Optional[str] = None
    temp_range: Optional[str] = None
    rain_prob: Optional[float] = None


class TripPlan(BaseModel):
    duration_days: int
    location: str
    days: List[TripDay] = []
    weather_aware: bool = False
    planning_mode: str = "standard"  # 'standard' | 'weather_optimized' | 'mock_mvp'


class ChatResponse(BaseModel):
    session_id: str
    status: str = "success"
    domain: Optional[str] = None
    location: Optional[str] = None
    prediction: Optional[str] = None
    recommendation: Optional[str] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    final_answer: Optional[str] = None
    trip_plan: Optional[TripPlan] = None  # V3: populated for trip planning queries
    error: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None
    evidence: Optional[List[str]] = None
    weather_stats: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, str]] = None
    weather_path: Optional[str] = None
    weather_confidence: Optional[float] = None
    weather_mode: Optional[str] = None
    sources_used: Optional[List[str]] = None
    sources_rejected: Optional[List[str]] = None
    weather_debug: Optional[Dict[str, Any]] = None
