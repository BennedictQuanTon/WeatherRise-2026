"""Provider comparison and disagreement detection."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from .schemas import SourceComparisonMatrix, StandardWeatherRecord, WeatherRequirement


NUMERIC_FIELDS = [
    "rain_probability",
    "temperature_c",
    "humidity_percent",
    "precipitation_mm",
    "wind_speed_kmh",
    "wind_gust_kmh",
    "visibility_km",
    "uv_index",
    "wave_height_m",
]


class SourceComparisonBuilder:
    """Compares source aggregate values for the same request/location window."""

    def build(
        self,
        requirement: WeatherRequirement,
        records: list[StandardWeatherRecord],
    ) -> SourceComparisonMatrix:
        by_source: dict[str, list[StandardWeatherRecord]] = defaultdict(list)
        for record in records:
            by_source[record.source_code].append(record)

        values: dict[str, dict[str, Any]] = {}
        for source_code, source_records in by_source.items():
            values[source_code] = self._aggregate(source_records)

        disagreement = self._disagreement(values)
        warnings = []
        major_conflict = False
        if disagreement.get("rain_probability_range", 0) >= 0.35:
            major_conflict = True
            warnings.append("Major rain probability disagreement detected.")
        if disagreement.get("temperature_c_range", 0) >= 6:
            major_conflict = True
            warnings.append("Major temperature disagreement detected.")
        if disagreement.get("wind_speed_kmh_range", 0) >= 20:
            major_conflict = True
            warnings.append("Major wind speed disagreement detected.")
        if disagreement.get("wave_height_m_range", 0) >= 1.0:
            major_conflict = True
            warnings.append("Major marine wave-height disagreement detected.")

        return SourceComparisonMatrix(
            request_id=requirement.request_id,
            location_name=requirement.location_name,
            forecast_time_local=requirement.start_time,
            compared_sources=sorted(values.keys()),
            values=values,
            disagreement=disagreement,
            major_conflict=major_conflict,
            warnings=warnings,
        )

    def _aggregate(self, records: list[StandardWeatherRecord]) -> dict[str, Any]:
        aggregate: dict[str, Any] = {}
        for field in NUMERIC_FIELDS:
            vals = [getattr(record, field) for record in records if getattr(record, field) is not None]
            if vals:
                if field in {"rain_probability", "precipitation_mm", "wind_speed_kmh", "wind_gust_kmh", "uv_index", "wave_height_m"}:
                    aggregate[field] = round(max(vals), 3)
                else:
                    aggregate[field] = round(mean(vals), 3)
        descriptions = [record.weather_description for record in records if record.weather_description]
        if descriptions:
            aggregate["weather_description"] = descriptions[0]
        return aggregate

    def _disagreement(self, values: dict[str, dict[str, Any]]) -> dict[str, Any]:
        disagreement: dict[str, Any] = {}
        for field in NUMERIC_FIELDS:
            vals = [source_values[field] for source_values in values.values() if isinstance(source_values.get(field), (int, float))]
            if len(vals) >= 2:
                disagreement[f"{field}_range"] = round(max(vals) - min(vals), 3)
                disagreement[f"{field}_mean"] = round(mean(vals), 3)
        return disagreement
