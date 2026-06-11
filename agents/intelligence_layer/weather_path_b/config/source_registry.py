"""Weather source registry for Path B.

Kept in Python so the project does not need a YAML parser dependency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_project_env() -> None:
    """Load Path B provider keys from local env files when available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    project_root = Path(__file__).resolve().parents[4]
    load_dotenv(project_root / ".env", override=False)
    load_dotenv(project_root / ".env.dev", override=False)
    load_dotenv(project_root / ".env.demo.local", override=True)


_load_project_env()


@dataclass(frozen=True)
class SourceConfig:
    source_code: str
    enabled: bool
    requires_key: bool
    env_keys: tuple[str, ...] = ()
    priority: int = 50
    timeout_seconds: int = 6
    supports: tuple[str, ...] = ()
    domain_triggers: tuple[str, ...] = ()
    historical_skill: float = 0.75
    resolution_score: float = 0.75
    metadata: dict[str, object] = field(default_factory=dict)

    def api_key(self) -> str | None:
        for env_key in self.env_keys:
            value = os.getenv(env_key)
            if value:
                return value
        return None


DEFAULT_SOURCE_REGISTRY: dict[str, SourceConfig] = {
    "open_meteo": SourceConfig(
        source_code="open_meteo",
        enabled=True,
        requires_key=False,
        priority=1,
        timeout_seconds=6,
        supports=("hourly_forecast", "daily_forecast", "historical"),
        historical_skill=0.82,
        resolution_score=0.78,
    ),
    "weatherapi": SourceConfig(
        source_code="weatherapi",
        enabled=True,
        requires_key=True,
        env_keys=("WEATHERAPI_KEY",),
        priority=2,
        timeout_seconds=6,
        supports=("current_weather", "three_day_forecast", "recent_history", "alerts"),
        historical_skill=0.78,
        resolution_score=0.75,
    ),
    "tomorrow_io": SourceConfig(
        source_code="tomorrow_io",
        enabled=True,
        requires_key=True,
        env_keys=("TOMORROW_IO_API_KEY",),
        priority=3,
        timeout_seconds=6,
        supports=("realtime", "forecast", "historical_recent", "hyperlocal_check"),
        historical_skill=0.80,
        resolution_score=0.86,
    ),
    "visual_crossing": SourceConfig(
        source_code="visual_crossing",
        enabled=True,
        requires_key=True,
        env_keys=("VISUAL_CROSSING_API_KEY",),
        priority=4,
        timeout_seconds=8,
        supports=("forecast", "historical", "alerts"),
        historical_skill=0.77,
        resolution_score=0.72,
    ),
    "openweathermap": SourceConfig(
        source_code="openweathermap",
        enabled=True,
        requires_key=True,
        env_keys=("OPENWEATHERMAP_API_KEY", "OWM_API_KEY"),
        priority=5,
        timeout_seconds=6,
        supports=("current_weather", "forecast", "alerts"),
        historical_skill=0.76,
        resolution_score=0.72,
    ),
    "stormglass": SourceConfig(
        source_code="stormglass",
        enabled=True,
        requires_key=True,
        env_keys=("STORMGLASS_API_KEY",),
        priority=6,
        timeout_seconds=8,
        supports=("marine_weather", "wave_height", "tides", "water_temperature"),
        domain_triggers=("beach", "island", "water_sports", "marine"),
        historical_skill=0.74,
        resolution_score=0.82,
    ),
    "seven_timer": SourceConfig(
        source_code="seven_timer",
        enabled=True,
        requires_key=False,
        priority=99,
        timeout_seconds=8,
        supports=("basic_forecast", "no_key_fallback"),
        historical_skill=0.55,
        resolution_score=0.45,
    ),
}


def get_source_registry() -> dict[str, SourceConfig]:
    """Return source config filtered by explicit disable env vars."""
    registry: dict[str, SourceConfig] = {}
    for code, config in DEFAULT_SOURCE_REGISTRY.items():
        flag = os.getenv(f"WEATHER_SOURCE_{code.upper()}_ENABLED")
        if flag is not None and flag.lower() in {"0", "false", "no", "off"}:
            registry[code] = SourceConfig(**{**config.__dict__, "enabled": False})
        else:
            registry[code] = config
    return registry
