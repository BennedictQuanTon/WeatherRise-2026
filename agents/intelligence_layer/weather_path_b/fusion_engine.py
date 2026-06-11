"""Weather fusion engine with conservative risk logic."""

from __future__ import annotations

from statistics import mean
from typing import Any

from .comparison_matrix import NUMERIC_FIELDS
from .schemas import FusedWeather, SourceComparisonMatrix, SourceScore, WeatherRequirement


class WeatherFusionEngine:
    """Builds the fused weather record from ranked valid source values."""

    def fuse(
        self,
        requirement: WeatherRequirement,
        comparison: SourceComparisonMatrix,
        scores: list[SourceScore],
        rejected_sources: list[str],
    ) -> FusedWeather:
        score_by_source = {score.source_code: max(score.rank_score, 0.01) for score in scores}
        fused: dict[str, Any] = {}
        warnings = list(comparison.warnings)

        for field in NUMERIC_FIELDS:
            weighted_values = []
            raw_values = []
            for source_code, source_values in comparison.values.items():
                value = source_values.get(field)
                if isinstance(value, (int, float)):
                    weight = score_by_source.get(source_code, 0.1)
                    weighted_values.append((float(value), weight))
                    raw_values.append(float(value))
            if weighted_values:
                total_weight = sum(weight for _, weight in weighted_values)
                fused_value = sum(value * weight for value, weight in weighted_values) / total_weight
                if requirement.safety_mode == "conservative" and field in {
                    "rain_probability",
                    "precipitation_mm",
                    "wind_speed_kmh",
                    "wind_gust_kmh",
                    "uv_index",
                    "wave_height_m",
                }:
                    fused_value = max(fused_value, max(raw_values) * 0.9)
                fused[field] = round(fused_value, 3)

        descriptions = [
            source_values.get("weather_description")
            for source_values in comparison.values.values()
            if source_values.get("weather_description")
        ]
        if descriptions:
            fused["weather_description"] = descriptions[0]

        confidence = self._confidence(comparison, scores, fused)
        if comparison.major_conflict:
            warnings.append("Fusion confidence reduced by major source conflict.")
        if requirement.safety_mode == "conservative":
            warnings.append("Conservative fusion applied for safety-sensitive weather planning.")

        return FusedWeather(
            request_id=requirement.request_id,
            location_name=requirement.location_name,
            forecast_time_local=requirement.start_time,
            fused_values=fused,
            fusion_method="weighted_score_conservative" if requirement.safety_mode == "conservative" else "weighted_score",
            sources_used=[score.source_code for score in scores],
            sources_rejected=rejected_sources,
            confidence=confidence,
            warnings=warnings,
        )

    def _confidence(
        self,
        comparison: SourceComparisonMatrix,
        scores: list[SourceScore],
        fused: dict[str, Any],
    ) -> float:
        if not fused or not scores:
            return 0.0
        base = mean([score.rank_score for score in scores])
        source_count_bonus = min(0.12, len(scores) * 0.03)
        conflict_penalty = 0.22 if comparison.major_conflict else 0.0
        return round(max(0.0, min(1.0, base + source_count_bonus - conflict_penalty)), 3)
