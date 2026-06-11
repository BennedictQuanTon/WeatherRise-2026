"""Quality validation for normalized Path B weather records."""

from __future__ import annotations

from collections import defaultdict

from .schemas import QualityReport, StandardWeatherRecord, WeatherRequirement


class WeatherQualityValidator:
    """Checks missing fields, ranges, units, and domain-critical variables."""

    BASE_FIELDS = ("temperature_c", "rain_probability", "wind_speed_kmh")

    def validate(
        self,
        records: list[StandardWeatherRecord],
        requirement: WeatherRequirement,
    ) -> tuple[list[StandardWeatherRecord], list[QualityReport]]:
        by_source: dict[str, list[StandardWeatherRecord]] = defaultdict(list)
        for record in records:
            by_source[record.source_code].append(record)

        valid_records: list[StandardWeatherRecord] = []
        reports: list[QualityReport] = []
        for source_code, source_records in by_source.items():
            missing = self._missing_fields(source_records, requirement)
            invalid = self._invalid_fields(source_records)
            warnings = []
            if len(source_records) == 0:
                warnings.append("No normalized records produced.")
            if missing:
                warnings.append(f"Missing critical fields: {', '.join(missing)}")
            if invalid:
                warnings.append(f"Invalid values detected: {', '.join(invalid)}")

            completeness = max(0.0, 1.0 - len(missing) / max(len(self._critical_fields(requirement)), 1))
            validity = 0.0 if invalid else 1.0
            volume = min(1.0, len(source_records) / 24.0)
            score = round((completeness * 0.45) + (validity * 0.4) + (volume * 0.15), 3)
            is_valid = score >= 0.45 and not invalid

            reports.append(
                QualityReport(
                    source_code=source_code,
                    valid=is_valid,
                    quality_score=score,
                    missing_fields=missing,
                    invalid_fields=invalid,
                    warnings=warnings,
                )
            )
            if is_valid:
                valid_records.extend(source_records)

        return valid_records, reports

    def _critical_fields(self, requirement: WeatherRequirement) -> list[str]:
        fields = list(dict.fromkeys([*self.BASE_FIELDS, *requirement.required_variables]))
        return [field for field in fields if field not in {"storm_alert"}]

    def _missing_fields(
        self,
        records: list[StandardWeatherRecord],
        requirement: WeatherRequirement,
    ) -> list[str]:
        missing = []
        for field in self._critical_fields(requirement):
            if not any(getattr(record, field, None) is not None for record in records):
                missing.append(field)
        return missing

    def _invalid_fields(self, records: list[StandardWeatherRecord]) -> list[str]:
        invalid: set[str] = set()
        for record in records:
            checks = {
                "temperature_c": (-80, 65),
                "feels_like_c": (-90, 75),
                "humidity_percent": (0, 100),
                "precipitation_mm": (0, 1000),
                "rain_probability": (0, 1),
                "wind_speed_kmh": (0, 400),
                "wind_gust_kmh": (0, 500),
                "wind_direction_deg": (0, 360),
                "pressure_hpa": (800, 1100),
                "visibility_km": (0, 100),
                "cloud_cover_percent": (0, 100),
                "uv_index": (0, 20),
                "wave_height_m": (0, 30),
                "water_temperature_c": (-5, 45),
            }
            for field, (min_value, max_value) in checks.items():
                value = getattr(record, field, None)
                if value is not None and not min_value <= value <= max_value:
                    invalid.add(field)
            if abs(record.latitude) > 90:
                invalid.add("latitude")
            if abs(record.longitude) > 180:
                invalid.add("longitude")
        return sorted(invalid)
