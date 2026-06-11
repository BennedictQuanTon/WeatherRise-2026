"""Source planning for Path B."""

from __future__ import annotations

from .config.source_registry import SourceConfig, get_source_registry
from .schemas import WeatherRequirement, WeatherSourcePlan, WeatherSourcePlanItem


class WeatherSourcePlanner:
    """Selects weather providers by domain, activity, source capability, and keys."""

    def __init__(self, registry: dict[str, SourceConfig] | None = None):
        self.registry = registry or get_source_registry()

    def plan(self, requirement: WeatherRequirement) -> WeatherSourcePlan:
        candidates = self._candidate_codes(requirement)
        selected: list[WeatherSourcePlanItem] = []
        skipped: list[dict] = []

        for code in candidates:
            config = self.registry.get(code)
            if not config:
                skipped.append({"source_code": code, "reason": "not_registered"})
                continue
            if not config.enabled:
                skipped.append({"source_code": code, "reason": "disabled"})
                continue
            if config.requires_key and not config.api_key():
                skipped.append({"source_code": code, "reason": "missing_api_key", "env_keys": list(config.env_keys)})
                continue
            selected.append(
                WeatherSourcePlanItem(
                    source_code=code,
                    reason=self._reason(code, requirement),
                    required=code == "open_meteo",
                    timeout_seconds=config.timeout_seconds,
                    priority=config.priority,
                )
            )

        selected.sort(key=lambda item: item.priority)
        return WeatherSourcePlan(
            request_id=requirement.request_id,
            selected_sources=selected,
            skipped_sources=skipped,
        )

    def _candidate_codes(self, requirement: WeatherRequirement) -> list[str]:
        domain = requirement.domain.lower()
        activity = (requirement.activity_type or "").lower()
        if domain == "construction":
            codes = ["open_meteo", "weatherapi", "openweathermap", "tomorrow_io", "visual_crossing", "seven_timer"]
        elif domain == "agriculture":
            codes = ["open_meteo", "visual_crossing", "weatherapi", "openweathermap", "seven_timer"]
        elif activity in {"beach", "island", "water_sports", "marine"}:
            codes = ["open_meteo", "weatherapi", "tomorrow_io", "stormglass", "visual_crossing", "openweathermap", "seven_timer"]
        elif activity == "mountain":
            codes = ["open_meteo", "tomorrow_io", "weatherapi", "visual_crossing", "openweathermap", "seven_timer"]
        else:
            codes = ["open_meteo", "weatherapi", "visual_crossing", "openweathermap", "tomorrow_io", "seven_timer"]
        return list(dict.fromkeys(codes))

    def _reason(self, code: str, requirement: WeatherRequirement) -> str:
        if code == "open_meteo":
            return "baseline no-key hourly forecast source"
        if code == "stormglass":
            return "marine/beach evidence for wave, tide, and water conditions"
        if code == "tomorrow_io":
            return "short-term hyperlocal cross-check"
        if code == "visual_crossing":
            return "forecast plus historical/contextual cross-check"
        if code == "weatherapi":
            return "forecast, current weather, and alerts cross-check"
        if code == "openweathermap":
            return "common forecast fallback and triangulation source"
        return "no-key emergency fallback"
