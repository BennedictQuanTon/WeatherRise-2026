"""Pydantic contracts for the Path B weather pipeline."""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class WeatherRequirement(BaseModel):
    request_id: str
    domain: str = "tourism"
    intent: str = "general"
    activity_type: Optional[str] = None
    location_name: str = "Unknown"
    latitude: float
    longitude: float
    timezone: str = "Asia/Ho_Chi_Minh"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    required_variables: list[str] = Field(default_factory=list)
    safety_mode: Literal["normal", "conservative"] = "normal"
    user_constraints: list[str] = Field(default_factory=list)
    raw_user_input: Optional[str] = None


class WeatherSourcePlanItem(BaseModel):
    source_code: str
    reason: str
    required: bool = False
    timeout_seconds: int = 6
    priority: int = 1


class WeatherSourcePlan(BaseModel):
    request_id: str
    selected_sources: list[WeatherSourcePlanItem]
    skipped_sources: list[dict[str, Any]] = Field(default_factory=list)


class RawWeatherResponse(BaseModel):
    request_id: str
    source_code: str
    status: Literal["success", "failed", "timeout", "skipped"]
    raw_payload: Optional[dict[str, Any]] = None
    raw_file_path: Optional[str] = None
    error_message: Optional[str] = None
    fetched_at_utc: str
    latency_ms: Optional[int] = None


class StandardWeatherRecord(BaseModel):
    request_id: str
    source_code: str
    location_name: str
    latitude: float
    longitude: float
    forecast_time_utc: str
    forecast_time_local: str
    fetched_at_utc: str
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    precipitation_mm: Optional[float] = None
    rain_probability: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    pressure_hpa: Optional[float] = None
    visibility_km: Optional[float] = None
    cloud_cover_percent: Optional[float] = None
    uv_index: Optional[float] = None
    wave_height_m: Optional[float] = None
    water_temperature_c: Optional[float] = None
    tide_height_m: Optional[float] = None
    tide_type: Optional[str] = None
    weather_code: Optional[str | int] = None
    weather_description: Optional[str] = None
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    raw_file_path: Optional[str] = None
    normalized_file_path: Optional[str] = None


class QualityReport(BaseModel):
    source_code: str
    valid: bool
    quality_score: float
    missing_fields: list[str] = Field(default_factory=list)
    invalid_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceScore(BaseModel):
    source_code: str
    rank_score: float
    completeness_score: float
    freshness_score: float
    source_agreement_score: float
    domain_relevance_score: float
    latency_score: float
    quality_score: float
    historical_skill_score: float
    resolution_score: float
    reason: str


class SourceComparisonMatrix(BaseModel):
    request_id: str
    location_name: str
    forecast_time_local: Optional[str] = None
    compared_sources: list[str]
    values: dict[str, dict[str, Any]] = Field(default_factory=dict)
    disagreement: dict[str, Any] = Field(default_factory=dict)
    major_conflict: bool = False
    warnings: list[str] = Field(default_factory=list)


class FusedWeather(BaseModel):
    request_id: str
    location_name: str
    forecast_time_local: Optional[str] = None
    fused_values: dict[str, Any]
    fusion_method: str
    sources_used: list[str]
    sources_rejected: list[str] = Field(default_factory=list)
    confidence: float
    warnings: list[str] = Field(default_factory=list)


class Earth2ProcessingReport(BaseModel):
    enabled: bool
    location_aligned: bool = False
    time_aligned: bool = False
    model_ready: bool = False
    missing_variables: list[str] = Field(default_factory=list)
    incompatible_sources: list[str] = Field(default_factory=list)
    processed_file_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    score: Optional[float] = None


class ArbiterDecision(BaseModel):
    selected_weather_mode: Literal[
        "fused_weather",
        "best_single_source",
        "conservative_risk",
        "latest_snapshot",
        "degraded_open_meteo_only",
        "weather_unavailable",
    ]
    best_individual_source: Optional[str] = None
    confidence: float
    arbiter_reason: str
    risk_interpretation: str
    warnings: list[str] = Field(default_factory=list)


class GoldWeatherDecision(BaseModel):
    request_id: str
    location_name: str
    forecast_time_local: Optional[str] = None
    selected_mode: str
    confidence: float
    sources_used: list[str]
    sources_rejected: list[str] = Field(default_factory=list)
    selected_weather: dict[str, Any]
    source_scores: list[SourceScore] = Field(default_factory=list)
    quality_reports: list[QualityReport] = Field(default_factory=list)
    comparison_matrix: Optional[SourceComparisonMatrix] = None
    fused_weather: Optional[FusedWeather] = None
    arbiter_decision: Optional[ArbiterDecision] = None
    earth2_processing_report: Optional[Earth2ProcessingReport] = None
    evidence_paths: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PathBRunArtifacts(BaseModel):
    requirement: WeatherRequirement
    source_plan: WeatherSourcePlan
    raw_responses: list[RawWeatherResponse] = Field(default_factory=list)
    normalized_records: list[StandardWeatherRecord] = Field(default_factory=list)
    gold_decision: GoldWeatherDecision
