"""Guarded Earth2Studio processing layer for Path B."""

from __future__ import annotations

import os

from .schemas import Earth2ProcessingReport, StandardWeatherRecord, WeatherRequirement


class Earth2StudioProcessingLayer:
    """Produces alignment/model-readiness reports without making Earth2 mandatory."""

    def process(
        self,
        requirement: WeatherRequirement,
        records: list[StandardWeatherRecord],
    ) -> Earth2ProcessingReport:
        enabled = os.getenv("EARTH2STUDIO_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
        missing_variables = [
            variable
            for variable in requirement.required_variables
            if not any(getattr(record, variable, None) is not None for record in records)
        ]
        if not enabled:
            return Earth2ProcessingReport(
                enabled=False,
                missing_variables=missing_variables,
                warnings=["Earth2Studio disabled; Path B continued with API evidence alignment only."],
                score=None,
            )

        try:
            import earth2studio  # type: ignore  # noqa: F401
        except Exception as exc:
            return Earth2ProcessingReport(
                enabled=True,
                location_aligned=bool(records),
                time_aligned=bool(records),
                model_ready=False,
                missing_variables=missing_variables,
                warnings=[f"Earth2Studio requested but unavailable: {exc}"],
                score=0.35 if records else 0.0,
            )

        return Earth2ProcessingReport(
            enabled=True,
            location_aligned=bool(records),
            time_aligned=bool(records),
            model_ready=bool(records) and not missing_variables,
            missing_variables=missing_variables,
            warnings=[] if records else ["No weather records available for Earth2Studio alignment."],
            score=0.85 if records and not missing_variables else 0.65 if records else 0.0,
        )
