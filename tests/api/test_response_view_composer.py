from types import SimpleNamespace

from apps.api.app.schemas.response_schema import ChatResponse
from apps.api.app.services.response_view_composer import ResponseViewComposer


def processed_payload(intent_subtype=None):
    return {
        "domain": "tourism",
        "intent": "travel_planning",
        "intent_subtype": intent_subtype,
        "location": "Hoi An",
        "geographical_location": {
            "coordinates": {"latitude": 15.8801, "longitude": 108.338}
        },
        "time_range": {
            "start": "2026-06-15",
            "end": "2026-06-17",
            "raw_text": "next week",
        },
        "mcp_context": {
            "weather_forecast": {
                "output": {
                    "daily_forecasts": [
                        {
                            "date": "2026-06-15",
                            "day_label": "Mon Jun 15",
                            "max_temp_c": 31,
                            "min_temp_c": 25,
                            "max_rain_prob_pct": 20,
                            "max_wind_kmh": 16,
                            "dominant_weather": "Partly cloudy",
                            "overall_risk": "low",
                        },
                        {
                            "date": "2026-06-16",
                            "day_label": "Tue Jun 16",
                            "max_temp_c": 30,
                            "min_temp_c": 24,
                            "max_rain_prob_pct": 45,
                            "max_wind_kmh": 18,
                            "dominant_weather": "Rain Chance",
                            "overall_risk": "medium",
                        },
                    ]
                }
            },
            "places": [
                {
                    "name": "Hoi An Museum",
                    "latitude": 15.879,
                    "longitude": 108.326,
                    "is_indoor": True,
                    "vibe_tags": ["culture"],
                }
            ],
        },
    }


def intelligence_output():
    return SimpleNamespace(
        prediction="Rain risk is low to medium.",
        recommendation="Visit outdoor places early. Keep an indoor backup.",
        explanation="Forecast based on deterministic weather evidence.",
        final_answer="Hoi An looks reasonable for travel with flexible timing.",
        risk_assessment={
            "rain_risk": "medium",
            "wind_risk": "low",
            "heat_risk": "low",
            "trip_disruption_risk": "medium",
        },
        metadata={},
    )


def test_weather_only_composer_returns_weather_prediction_view():
    payload = ResponseViewComposer().compose(
        processed=processed_payload(),
        intent_subtype=None,
        intelligence_output=intelligence_output(),
        trip_plan=None,
        coordinates={"latitude": 15.8801, "longitude": 108.338},
        time_range={"start": "2026-06-15", "end": "2026-06-17", "raw_text": "next week"},
        weather_stats={},
        weather_debug={},
    )

    assert payload["response_type"] == "weather_prediction"
    assert payload["trip_view"] is None
    assert payload["weather_view"]["location"]["name"] == "Hoi An"
    assert payload["weather_view"]["daily_forecast"][0]["rain_probability"] == 0.2
    assert payload["weather_view"]["map"]["markers"][0]["temperature_c"] is not None


def test_trip_composer_returns_trip_planning_view_with_stop_coordinates():
    trip_plan = {
        "duration_days": 1,
        "location": "Da Nang",
        "days": [
            {
                "day": 1,
                "theme": "Culture & food",
                "date": "2026-06-15",
                "stops": [
                    {
                        "order": 1,
                        "name": "Banh Mi Ba Lan",
                        "lat": 16.067,
                        "lon": 108.22,
                        "time_block": "breakfast",
                        "planned_time": "07:30",
                        "category": "restaurant",
                        "is_indoor": True,
                    }
                ],
            }
        ],
    }

    payload = ResponseViewComposer().compose(
        processed=processed_payload(intent_subtype="multi_day_trip_planning"),
        intent_subtype="multi_day_trip_planning",
        intelligence_output=intelligence_output(),
        trip_plan=trip_plan,
        coordinates={"latitude": 16.0544, "longitude": 108.2022},
        time_range={"start": "2026-06-15", "end": "2026-06-15", "raw_text": "next week"},
        weather_stats={},
        weather_debug={},
    )

    assert payload["response_type"] == "trip_planning"
    assert payload["weather_view"] is None
    assert payload["trip_view"]["days"][0]["stops"][0]["latitude"] == 16.067
    assert payload["trip_view"]["map"]["markers"][0]["label"] == "Banh Mi Ba Lan"


def test_chat_response_accepts_response_language():
    response = ChatResponse(session_id="s1", response_language="vi")

    assert response.response_language == "vi"
