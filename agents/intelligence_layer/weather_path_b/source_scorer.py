"""Source scoring for Path B."""

from __future__ import annotations

from collections import defaultdict

from .config.source_registry import SourceConfig, get_source_registry
from .schemas import QualityReport, RawWeatherResponse, SourceScore, StandardWeatherRecord, WeatherRequirement


class SourceScorer:
    """Scores each valid provider on quality, freshness, priority, latency, and relevance."""

    def __init__(self, registry: dict[str, SourceConfig] | None = None):
        self.registry = registry or get_source_registry()

    def score(
        self,
        requirement: WeatherRequirement,
        records: list[StandardWeatherRecord],
        quality_reports: list[QualityReport],
        raw_responses: list[RawWeatherResponse],
    ) -> list[SourceScore]:
        records_by_source: dict[str, list[StandardWeatherRecord]] = defaultdict(list)
        for record in records:
            records_by_source[record.source_code].append(record)
        quality_by_source = {report.source_code: report for report in quality_reports}
        raw_by_source = {raw.source_code: raw for raw in raw_responses}
        scores: list[SourceScore] = []

        for source_code, source_records in records_by_source.items():
            config = self.registry.get(source_code)
            quality = quality_by_source.get(source_code)
            raw = raw_by_source.get(source_code)
            quality_score = quality.quality_score if quality else 0.5
            completeness = self._completeness(requirement, source_records)
            freshness = 1.0 if source_records else 0.0
            domain_relevance = self._domain_relevance(requirement, source_code)
            latency = self._latency_score(raw.latency_ms if raw else None)
            historical = config.historical_skill if config else 0.65
            resolution = config.resolution_score if config else 0.65
            source_agreement = 1.0

            rank = round(
                quality_score * 0.28
                + completeness * 0.18
                + freshness * 0.12
                + domain_relevance * 0.14
                + latency * 0.08
                + historical * 0.1
                + resolution * 0.1,
                3,
            )
            scores.append(
                SourceScore(
                    source_code=source_code,
                    rank_score=rank,
                    completeness_score=round(completeness, 3),
                    freshness_score=round(freshness, 3),
                    source_agreement_score=source_agreement,
                    domain_relevance_score=round(domain_relevance, 3),
                    latency_score=round(latency, 3),
                    quality_score=round(quality_score, 3),
                    historical_skill_score=round(historical, 3),
                    resolution_score=round(resolution, 3),
                    reason=f"{source_code} scored {rank} from quality, completeness, relevance, latency, skill, and resolution.",
                )
            )
        return sorted(scores, key=lambda item: item.rank_score, reverse=True)

    def _completeness(self, requirement: WeatherRequirement, records: list[StandardWeatherRecord]) -> float:
        fields = list(dict.fromkeys(requirement.required_variables))
        present = sum(1 for field in fields if any(getattr(record, field, None) is not None for record in records))
        return present / max(len(fields), 1)

    def _domain_relevance(self, requirement: WeatherRequirement, source_code: str) -> float:
        if requirement.activity_type == "beach" and source_code == "stormglass":
            return 1.0
        if requirement.activity_type == "beach" and source_code in {"tomorrow_io", "weatherapi"}:
            return 0.9
        if requirement.domain == "construction" and source_code in {"weatherapi", "openweathermap", "tomorrow_io"}:
            return 0.86
        if requirement.domain == "agriculture" and source_code in {"visual_crossing", "weatherapi"}:
            return 0.86
        if source_code == "open_meteo":
            return 0.82
        if source_code == "seven_timer":
            return 0.45
        return 0.74

    def _latency_score(self, latency_ms: int | None) -> float:
        if latency_ms is None:
            return 0.5
        if latency_ms <= 700:
            return 1.0
        if latency_ms <= 2000:
            return 0.8
        if latency_ms <= 5000:
            return 0.55
        return 0.25
