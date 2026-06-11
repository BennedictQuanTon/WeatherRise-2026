import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from agents.context_agents.tourism_agent.agent import TourismContextAgent
from apps.api.app.schemas.context_schema import ParserOutput, TimeRange, GeographicalLocation, TripRequest

@pytest.fixture
def parser_output():
    return ParserOutput(
        domain="tourism",
        intent="general",
        intent_subtype="multi_day_trip_planning",
        location="Hoi An",
        geographical_location=GeographicalLocation(),
        time_range=TimeRange(raw_text="next weekend"),
        raw_user_input="Plan a trip to Hoi An next weekend",
        trip_request=TripRequest(duration_days=2, preferences=[])
    )

@pytest.mark.anyio
async def test_tourism_agent_kb_sparse_fallback(parser_output, monkeypatch):
    """Test that when KB returns sparse data, the agent correctly queries MCP and merges results."""
    
    agent = TourismContextAgent()

    # Mock the MCP caller
    async def mock_call_mcp(route, payload):
        if route == "location.resolveCoordinates":
            return {"output": {"latitude": 15.8801, "longitude": 108.3380}}
        elif route == "time.resolveTimeRange":
            return {"output": {"start": "2026-06-20", "end": "2026-06-22"}}
        elif route == "weather.getForecast":
            return {"weather": "mocked"}
        elif route == "place.searchPlaces":
            return {
                "provider": "mcp_place_search",
                "output": {
                    "attractions": [
                        {"place_id": "mcp_attr_1", "name": "MCP Attraction 1", "latitude": 15.8, "longitude": 108.3}
                    ]
                }
            }
        elif route == "place.searchRestaurants":
            return {
                "output": {
                    "restaurants": [
                        {"place_id": "mcp_rest_1", "name": "MCP Restaurant 1", "latitude": 15.8, "longitude": 108.3}
                    ]
                }
            }
        return {}

    monkeypatch.setattr(agent, "call_mcp", mock_call_mcp)

    # Mock the KB retriever to return sparse data
    class MockRetriever:
        async def get_attractions(self, **kwargs):
            mock_data = MagicMock()
            mock_data.data = [{"place_id": "kb_attr_1", "name": "KB Attraction 1"}]
            mock_data.source = "mock"
            return mock_data

        async def get_restaurants(self, **kwargs):
            mock_data = MagicMock()
            mock_data.data = []
            mock_data.source = "mock"
            return mock_data

    monkeypatch.setattr(agent, "_retriever", MockRetriever())

    # Run process
    processed_payload = await agent.process(parser_output)

    # Assertions
    mcp_context = processed_payload.mcp_context
    assert mcp_context is not None
    assert getattr(mcp_context, "coordinates", None) is not None
    assert mcp_context.coordinates["latitude"] == 15.8801

    trip_plan_context = getattr(mcp_context, "trip_plan_context", None)
    assert trip_plan_context is not None

    # KB returned 1 attraction, MCP returned 1, should be merged
    assert "MCP Attraction 1" in str(trip_plan_context)
    assert "MCP Restaurant 1" in str(trip_plan_context)
