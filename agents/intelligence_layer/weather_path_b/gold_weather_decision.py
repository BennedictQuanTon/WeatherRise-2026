"""Gold Weather Decision builder and adapters."""

from __future__ import annotations

from typing import Any

from agents.intelligence_layer.schemas import CanonicalWeatherData, CanonicalWeatherPoint

from .schemas import (
    ArbiterDecision,
    Earth2ProcessingReport,
    FusedWeather,
    GoldWeatherDecision,
    QualityReport,
    SourceComparisonMatrix,
    SourceScore,
    StandardWeatherRecord,
    WeatherRequirement,
)


class GoldWeatherDecisionBuilder:
    """Builds the final trusted weather package from Path B artifacts."""

    def build(
        self,
        requirement: WeatherRequirement,
        valid_records: list[StandardWeatherRecord],
        source_scores: list[SourceScore],
        quality_reports: list[QualityReport],
        comparison_matrix: SourceComparisonMatrix,
        fused_weather: FusedWeather,
        arbiter_decision: ArbiterDecision,
        earth2_processing_report: Earth2ProcessingReport,
        evidence_paths: dict[str, Any],
        extra_warnings: list[str] | None = None,
    ) -> GoldWeatherDecision:
        selected_weather = self._select_weather(valid_records, fused_weather, arbiter_decision)
        warnings = [
            *fused_weather.warnings,
            *arbiter_decision.warnings,
            *(earth2_processing_report.warnings or []),
            *(extra_warnings or []),
        ]
        return GoldWeatherDecision(
            request_id=requirement.request_id,
            location_name=requirement.location_name,
            forecast_time_local=requirement.start_time,
            selected_mode=arbiter_decision.selected_weather_mode,
            confidence=round(min(fused_weather.confidence, arbiter_decision.confidence), 3),
            sources_used=fused_weather.sources_used,
            sources_rejected=fused_weather.sources_rejected,
            selected_weather=selected_weather,
            source_scores=source_scores,
            quality_reports=quality_reports,
            comparison_matrix=comparison_matrix,
            fused_weather=fused_weather,
            arbiter_decision=arbiter_decision,
            earth2_processing_report=earth2_processing_report,
            evidence_paths=evidence_paths,
            warnings=list(dict.fromkeys(warnings)),
        )

    def unavailable(
        self,
        requirement: WeatherRequirement,
        quality_reports: list[QualityReport] | None = None,
        warnings: list[str] | None = None,
    ) -> GoldWeatherDecision:
        return GoldWeatherDecision(
            request_id=requirement.request_id,
            location_name=requirement.location_name,
            forecast_time_local=requirement.start_time,
            selected_mode="weather_unavailable",
            confidence=0.0,
            sources_used=[],
            selected_weather={},
            quality_reports=quality_reports or [],
            evidence_paths={},
            warnings=warnings or ["Weather evidence unavailable."],
        )

    def _select_weather(
        self,
        valid_records: list[StandardWeatherRecord],
        fused_weather: FusedWeather,
        arbiter_decision: ArbiterDecision,
    ) -> dict[str, Any]:
        if arbiter_decision.selected_weather_mode in {"fused_weather", "conservative_risk"}:
            return dict(fused_weather.fused_values)
        if arbiter_decision.best_individual_source:
            for record in valid_records:
                if record.source_code == arbiter_decision.best_individual_source:
                    return _record_weather(record)
        if valid_records:
            return _record_weather(valid_records[0])
        return {}


def gold_decision_to_canonical(
    gold: GoldWeatherDecision,
    requirement: WeatherRequirement | None = None,
) -> CanonicalWeatherData:
    """Adapt GoldWeatherDecision to existing CanonicalWeatherData.

    The existing PredictionEngine thresholds expect rain_probability as a
    percentage, while Path B records keep it as 0.0-1.0.
    """
    selected = gold.selected_weather or {}
    rain_probability = selected.get("rain_probability")
    if isinstance(rain_probability, (int, float)) and rain_probability <= 1:
        rain_probability = round(rain_probability * 100, 3)

    point = CanonicalWeatherPoint(
        time=gold.forecast_time_local or (requirement.start_time if requirement else "") or "",
        temperature_c=selected.get("temperature_c"),
        rain_probability=rain_probability,
        precipitation_mm=selected.get("precipitation_mm"),
        wind_speed_kmh=selected.get("wind_speed_kmh"),
        wind_gust_kmh=selected.get("wind_gust_kmh"),
        humidity_percent=selected.get("humidity_percent"),
        weather_code=selected.get("weather_code") if isinstance(selected.get("weather_code"), int) else None,
        storm_risk=selected.get("storm_risk"),
    )
    return CanonicalWeatherData(
        source="path_b_gold_weather_decision",
        source_type=gold.selected_mode,
        location={
            "name": gold.location_name,
            "latitude": requirement.latitude if requirement else None,
            "longitude": requirement.longitude if requirement else None,
            "timezone": requirement.timezone if requirement else None,
        },
        forecast_window={
            "start": requirement.start_time if requirement and requirement.start_time else gold.forecast_time_local or "",
            "end": requirement.end_time if requirement and requirement.end_time else gold.forecast_time_local or "",
        },
        resolution={"temporal": "path_b_fused", "spatial": "multi_source"},
        variables=[point] if selected else [],
        data_quality={
            "confidence": gold.confidence,
            "sources_used": gold.sources_used,
            "sources_rejected": gold.sources_rejected,
            "selected_mode": gold.selected_mode,
            "warnings": gold.warnings,
            "evidence_paths": gold.evidence_paths,
        },
    )


def build_weather_debug(gold: GoldWeatherDecision) -> dict[str, Any]:
    return {
        "request_id": gold.request_id,
        "weather_path": "path_b",
        "selected_mode": gold.selected_mode,
        "confidence": gold.confidence,
        "sources_used": gold.sources_used,
        "sources_rejected": gold.sources_rejected,
        "source_scores": [score.model_dump() for score in gold.source_scores],
        "quality_reports": [report.model_dump() for report in gold.quality_reports],
        "comparison_matrix": gold.comparison_matrix.model_dump() if gold.comparison_matrix else None,
        "fused_weather": gold.fused_weather.model_dump() if gold.fused_weather else None,
        "arbiter_decision": gold.arbiter_decision.model_dump() if gold.arbiter_decision else None,
        "earth2_processing_report": gold.earth2_processing_report.model_dump() if gold.earth2_processing_report else None,
        "selected_weather": gold.selected_weather,
        "evidence_paths": gold.evidence_paths,
        "warnings": gold.warnings,
    }


def _record_weather(record: StandardWeatherRecord) -> dict[str, Any]:
    fields = [
        "temperature_c",
        "feels_like_c",
        "humidity_percent",
        "precipitation_mm",
        "rain_probability",
        "wind_speed_kmh",
        "wind_gust_kmh",
        "wind_direction_deg",
        "pressure_hpa",
        "visibility_km",
        "cloud_cover_percent",
        "uv_index",
        "wave_height_m",
        "water_temperature_c",
        "tide_height_m",
        "tide_type",
        "weather_code",
        "weather_description",
    ]
    return {field: getattr(record, field) for field in fields if getattr(record, field) is not None}
