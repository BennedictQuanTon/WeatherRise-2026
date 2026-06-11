from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


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


class LocationPoint(BaseModel):
    name: str
    latitude: float
    longitude: float


class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    label: Optional[str] = None


class MapMarker(BaseModel):
    id: str
    label: str
    latitude: float
    longitude: float
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    category: Optional[str] = None
    temperature_c: Optional[float] = None
    weather_condition: Optional[str] = None
    rain_probability: Optional[float] = None
    is_indoor: Optional[bool] = None


class WeatherAssumption(BaseModel):
    summary: str
    should_go: bool
    decision_label: str
    reason: str


class WeatherStatistics(BaseModel):
    avg_temperature_c: Optional[float] = None
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    avg_wind_kmh: Optional[float] = None
    total_rainfall_mm: Optional[float] = None
    rain_risk: Optional[str] = None
    wind_risk: Optional[str] = None
    heat_risk: Optional[str] = None
    overall_risk: Optional[str] = None
    most_common_condition: Optional[str] = None


class DailyForecastItem(BaseModel):
    date: str
    day_label: str
    condition: str
    condition_icon: str
    max_temp_c: Optional[float] = None
    min_temp_c: Optional[float] = None
    wind_kmh: Optional[float] = None
    rain_probability: Optional[float] = None
    rain_mm: Optional[float] = None
    risk: Optional[str] = None


class WeatherAlternative(BaseModel):
    name: str
    description: str
    distance_label: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WeatherInsight(BaseModel):
    title: str
    body: str
    type: Literal["rain", "wind", "heat", "travel", "general"] = "general"


class WeatherMap(BaseModel):
    center: LocationPoint
    markers: List[MapMarker] = Field(default_factory=list)


class WeatherPredictionView(BaseModel):
    title: str
    location: LocationPoint
    date_range: DateRange
    assumption: WeatherAssumption
    statistics: WeatherStatistics
    daily_forecast: List[DailyForecastItem] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    alternatives: List[WeatherAlternative] = Field(default_factory=list)
    map: WeatherMap
    insights: List[WeatherInsight] = Field(default_factory=list)


class TripSummaryCards(BaseModel):
    avg_high_c: Optional[float] = None
    avg_low_c: Optional[float] = None
    avg_wind_kmh: Optional[float] = None
    humidity_percent: Optional[float] = None
    rain_risk: Optional[str] = None


class TripViewDayWeather(BaseModel):
    high_c: Optional[float] = None
    low_c: Optional[float] = None
    rain_probability: Optional[float] = None
    condition: Optional[str] = None


class TripViewStop(BaseModel):
    order: int
    time: str
    time_block: str
    category: str
    name: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    forecast_temp_c: Optional[float] = None
    rain_probability: Optional[float] = None
    weather_condition: Optional[str] = None
    is_indoor: bool = False
    weather_suitability: Optional[str] = None


class TripViewDay(BaseModel):
    day: int
    date: Optional[str] = None
    title: str
    summary: str
    weather: TripViewDayWeather
    stops: List[TripViewStop] = Field(default_factory=list)


class TripMap(BaseModel):
    markers: List[MapMarker] = Field(default_factory=list)


class TripPlanningView(BaseModel):
    title: str
    date_range: DateRange
    summary_cards: TripSummaryCards
    ai_summary: str
    days: List[TripViewDay] = Field(default_factory=list)
    map: TripMap


class ChatResponse(BaseModel):
    session_id: str
    status: str = "success"
    response_type: Literal["weather_prediction", "trip_planning", "general"] = "general"
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
    response_language: Optional[Literal["en", "vi"]] = None
    weather_view: Optional[WeatherPredictionView] = None
    trip_view: Optional[TripPlanningView] = None
