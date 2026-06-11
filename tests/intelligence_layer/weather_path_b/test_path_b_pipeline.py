import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents.intelligence_layer.weather_path_b.clients import BaseWeatherClient
from agents.intelligence_layer.weather_path_b.config.source_registry import get_source_registry
from agents.intelligence_layer.weather_path_b.gold_weather_decision import gold_decision_to_canonical
from agents.intelligence_layer.weather_path_b.multi_source_weather_fetcher import MultiSourceWeatherFetcher
from agents.intelligence_layer.weather_path_b.nim_weather_arbiter import NIMWeatherArbiter
from agents.intelligence_layer.weather_path_b.normalizers import SourceSpecificNormalizer
from agents.intelligence_layer.weather_path_b.path_b_service import PathBWeatherService
from agents.intelligence_layer.weather_path_b.quality_validator import WeatherQualityValidator
from agents.intelligence_layer.weather_path_b.schemas import (
    ArbiterDecision,
    Earth2ProcessingReport,
    FusedWeather,
    RawWeatherResponse,
    SourceComparisonMatrix,
    StandardWeatherRecord,
)
from agents.intelligence_layer.weather_path_b.weather_requirement_reader import WeatherRequirementReader
from agents.intelligence_layer.weather_path_b.weather_source_planner import WeatherSourcePlanner
from apps.api.app.schemas.response_schema import ChatResponse


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    with (FIXTURES / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def processed_payload(raw_user_input: str = "Plan a 3-day trip to Da Nang and avoid rain") -> dict:
    return {
        "domain": "tourism",
        "intent": "travel_planning",
        "location": "Da Nang",
        "geographical_location": {"coordinates": {"latitude": 16.0544, "longitude": 108.2022}},
        "time_range": {"start": "2026-06-15", "end": "2026-06-17", "timezone": "Asia/Ho_Chi_Minh"},
        "involved_context": ["weather_forecast", "tourist_attractions"],
        "knowledge_context": {},
        "mcp_context": {},
        "intelligence_requirements": {
            "realtime_weather_needed": True,
            "weather_variables": ["rain_probability", "temperature", "wind_speed", "humidity"],
            "reasoning_task": "tourism_multi_day_trip_planning",
        },
        "user_constraints": ["avoid rain"],
        "raw_user_input": raw_user_input,
    }


class FixtureWeatherClient(BaseWeatherClient):
    source_code = "fixture"
    fixture_name = ""

    async def _fetch_payload(self, requirement):
        return fixture(self.fixture_name)


def fixture_client(source_code: str, fixture_name: str):
    return type(
        f"{source_code.title().replace('_', '')}FixtureClient",
        (FixtureWeatherClient,),
        {"source_code": source_code, "fixture_name": fixture_name},
    )


class InvalidNIMClient:
    async def chat(self, messages):
        from agents.intelligence_layer.schemas import NIMResponse

        return NIMResponse(model="fake", content="not json", error=None)


def test_source_planner_skips_missing_keys(monkeypatch):
    for key in ["WEATHERAPI_KEY", "TOMORROW_IO_API_KEY", "VISUAL_CROSSING_API_KEY", "OPENWEATHERMAP_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    requirement = WeatherRequirementReader().read(processed_payload())
    plan = WeatherSourcePlanner().plan(requirement)

    selected = [item.source_code for item in plan.selected_sources]
    skipped = {item["source_code"]: item["reason"] for item in plan.skipped_sources}

    assert "open_meteo" in selected
    assert "seven_timer" in selected
    assert skipped["weatherapi"] == "missing_api_key"


def test_normalizers_convert_units_and_probability():
    requirement = WeatherRequirementReader().read(processed_payload())
    raw = RawWeatherResponse(
        request_id=requirement.request_id,
        source_code="openweathermap",
        status="success",
        raw_payload=fixture("openweathermap_danang.json"),
        fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        latency_ms=25,
    )
    records = SourceSpecificNormalizer().normalize([raw], requirement)

    assert records[0].rain_probability == 0.71
    assert records[0].wind_speed_kmh == pytest.approx(19.8)
    assert records[0].visibility_km == 9


def test_quality_validator_rejects_impossible_values():
    requirement = WeatherRequirementReader().read(processed_payload())
    bad = StandardWeatherRecord(
        request_id=requirement.request_id,
        source_code="bad_source",
        location_name="Da Nang",
        latitude=16.0544,
        longitude=108.2022,
        forecast_time_utc="2026-06-15T10:00:00Z",
        forecast_time_local="2026-06-15T10:00:00+07:00",
        fetched_at_utc=datetime.now(timezone.utc).isoformat(),
        temperature_c=120,
        rain_probability=1.4,
        wind_speed_kmh=-1,
    )

    valid, reports = WeatherQualityValidator().validate([bad], requirement)

    assert valid == []
    assert not reports[0].valid
    assert "temperature_c" in reports[0].invalid_fields
    assert "rain_probability" in reports[0].invalid_fields


def test_path_b_service_end_to_end_with_fixtures(monkeypatch, tmp_path):
    monkeypatch.setenv("WEATHERAPI_KEY", "test")
    monkeypatch.setenv("TOMORROW_IO_API_KEY", "test")
    monkeypatch.setenv("VISUAL_CROSSING_API_KEY", "test")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test")
    monkeypatch.setenv("WEATHER_EVIDENCE_DIR", str(tmp_path / "weather_evidence"))
    monkeypatch.setenv("NIM_WEATHER_ARBITER_ENABLED", "false")

    clients = {
        "open_meteo": fixture_client("open_meteo", "open_meteo_danang.json"),
        "weatherapi": fixture_client("weatherapi", "weatherapi_danang.json"),
        "tomorrow_io": fixture_client("tomorrow_io", "tomorrow_io_danang.json"),
        "visual_crossing": fixture_client("visual_crossing", "visual_crossing_danang.json"),
        "openweathermap": fixture_client("openweathermap", "openweathermap_danang.json"),
        "seven_timer": fixture_client("seven_timer", "seven_timer_danang.json"),
    }
    registry = get_source_registry()
    fetcher = MultiSourceWeatherFetcher(registry=registry, clients=clients)
    service = PathBWeatherService(fetcher=fetcher, arbiter=NIMWeatherArbiter(enabled=False))

    gold = asyncio.run(service.run(processed_payload()))
    canonical = gold_decision_to_canonical(gold, WeatherRequirementReader().read(processed_payload()))

    assert gold.selected_mode == "fused_weather"
    assert gold.confidence > 0.5
    assert "open_meteo" in gold.sources_used
    assert gold.selected_weather["rain_probability"] > 0.6
    assert canonical.variables[0].rain_probability > 60
    assert (tmp_path / "weather_evidence" / "manifest.jsonl").exists()


def test_arbiter_invalid_json_uses_deterministic_fallback():
    arbiter = NIMWeatherArbiter(enabled=True, nim_client=InvalidNIMClient())
    requirement = WeatherRequirementReader().read(processed_payload())
    fused = FusedWeather(
        request_id=requirement.request_id,
        location_name="Da Nang",
        fused_values={"rain_probability": 0.74},
        fusion_method="weighted_score",
        sources_used=["open_meteo", "weatherapi"],
        confidence=0.8,
    )
    comparison = SourceComparisonMatrix(
        request_id=requirement.request_id,
        location_name=requirement.location_name,
        compared_sources=["open_meteo", "weatherapi"],
    )
    earth2 = Earth2ProcessingReport(enabled=False)

    decision = asyncio.run(arbiter.decide(requirement, [], [], comparison, fused, earth2, []))

    assert decision.selected_weather_mode == "fused_weather"
    assert "fallback" in decision.warnings[0].lower()


def test_chat_response_accepts_path_b_metadata():
    response = ChatResponse(
        session_id="s1",
        weather_path="path_b",
        weather_confidence=0.82,
        weather_mode="fused_weather",
        sources_used=["open_meteo", "weatherapi"],
        sources_rejected=["stormglass"],
        weather_debug={"selected_mode": "fused_weather"},
    )

    assert response.weather_path == "path_b"
    assert response.weather_debug["selected_mode"] == "fused_weather"
