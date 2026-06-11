import pytest
import asyncio
from typing import Dict, Any

from apps.api.app.services.pipeline_service import run_pipeline
from apps.api.app.schemas.context_schema import ParserOutput, TimeRange, GeographicalLocation

@pytest.mark.anyio
async def test_run_pipeline_schema_transfer(monkeypatch):
    """
    Test E2E flow from Parser -> Orchestrator -> Intelligence Layer -> Output
    Mocks NIMs to ensure it's fast and deterministic.
    """
    
    # 1. Mock Parser
    class MockParser:
        async def parse(self, text: str) -> ParserOutput:
            return ParserOutput(
                domain="tourism",
                intent="general",
                intent_subtype="multi_day_trip_planning",
                location="Da Nang",
                geographical_location=GeographicalLocation(),
                time_range=TimeRange(raw_text="tomorrow"),
                raw_user_input="Plan a trip to Da Nang tomorrow",
                trip_request=None
            )
            
    # 2. Mock Intelligence Service
    class MockIntelligenceOutput:
        prediction = "Medium Risk"
        recommendation = "Bring an umbrella"
        risk_assessment = {"rain_risk": "high"}
        explanation = "mocked"
        final_answer = "mocked answer"
        metadata = {
            "weather_path": "path_b",
            "weather_mode": "fused_weather",
            "weather_confidence": 0.9,
            "sources_used": ["mock_source"]
        }

    class MockIntelligenceService:
        async def reason(self, processed_payload):
            return MockIntelligenceOutput()

    # Apply Mocks to pipeline_service globals
    import apps.api.app.services.pipeline_service as ps
    monkeypatch.setattr(ps, "_parser", MockParser())
    monkeypatch.setattr(ps, "_intelligence", MockIntelligenceService())

    # We also need to mock Orchestrator's Context Agent call to avoid actual MCP/KB calls
    class MockTourismAgent:
        async def run(self, parsed):
            from apps.api.app.schemas.context_schema import FullyProcessedPayload, MCPContext
            mcp_ctx = MCPContext()
            mcp_ctx.trip_plan_context = {
                "duration_days": 1,
                "location": "Da Nang",
                "days": [{
                    "day": 1,
                    "stops": [
                        {"place_id": "1", "name": "Dragon Bridge", "time_block": "morning"}
                    ]
                }]
            }
            return FullyProcessedPayload(
                domain="tourism",
                intent="general",
                location="Da Nang",
                involved_context=["weather_forecast"],
                mcp_context=mcp_ctx
            )
            
    class MockOrchestrator:
        async def run(self, parsed):
            agent = MockTourismAgent()
            return await agent.run(parsed)
            
    monkeypatch.setattr(ps, "_orchestrator", MockOrchestrator())
    
    # 3. Run Pipeline
    result = await run_pipeline("Plan a trip to Da Nang tomorrow", "test_session_id")
    
    # 4. Assert Output Schema
    assert result["domain"] == "tourism"
    assert result["intent_subtype"] == "multi_day_trip_planning"
    assert result["prediction"] == "Medium Risk"
    assert result["weather_path"] == "path_b"
    assert result["weather_mode"] == "fused_weather"
    assert result["trip_plan"] is not None
    assert result["trip_plan"]["location"] == "Da Nang"
    assert len(result["trip_plan"]["days"]) == 1
    assert result["trip_plan"]["days"][0]["stops"][0]["name"] == "Dragon Bridge"
