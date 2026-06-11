import asyncio
import json
from types import SimpleNamespace

from agents.intelligence_layer.intelligence_service import IntelligenceService
from agents.intelligence_layer.language_detection import detect_response_language
from agents.intelligence_layer.schemas import IntelligenceOutput, NIMResponse, RiskLevel
from agents.intelligence_layer.vietnamese_localizer import QwenVietnameseLocalizer


def output_fixture() -> IntelligenceOutput:
    return IntelligenceOutput(
        prediction="Rain risk is medium and wind risk is low.",
        recommendation="Visit outdoor places early and keep indoor backups.",
        explanation="Generated from deterministic weather risk scoring.",
        final_answer="Hoi An is reasonable for travel with flexible timing.",
        risk_assessment={
            "rain_risk": RiskLevel.medium,
            "wind_risk": RiskLevel.low,
            "heat_risk": RiskLevel.low,
        },
        metadata={
            "weather_stats": {"max_rain_prob": 45, "max_temp": 31, "max_wind_speed": 18},
            "sources_used": ["open_meteo", "weatherapi"],
            "llm_text_fragments": {
                "recommendation_bullets": ["Visit outdoor places early."],
            },
        },
    )


class FakeQwenClient:
    def __init__(self, content: str):
        self.content = content
        self.calls = 0

    async def chat(self, messages):
        self.calls += 1
        return NIMResponse(
            model="fake-qwen",
            content=self.content,
            latency_ms=12,
        )


class RecordingLocalizer:
    def __init__(self):
        self.calls = 0

    async def localize(self, output):
        self.calls += 1
        metadata = dict(output.metadata)
        metadata.update({
            "response_language": "vi",
            "localization_model": "fake-qwen",
            "localization_source": "qwen_localizer",
        })
        return output.model_copy(update={"final_answer": "Câu trả lời tiếng Việt.", "metadata": metadata})


def test_vietnamese_detector_is_conservative():
    assert detect_response_language("Tuần sau Hội An thời tiết thế nào, có nên đi du lịch không?") == "vi"
    assert detect_response_language("toi muon di du lich Da Nang va tranh mua") == "vi"
    assert detect_response_language("What is the weather around Hoi An next week?") == "en"
    assert detect_response_language("Da Nang next week weather?") == "en"


def test_qwen_localizer_success_translates_text_and_preserves_structured_metadata():
    localized_json = {
        "prediction": "Rủi ro mưa ở mức trung bình và rủi ro gió thấp.",
        "recommendation": "Nên đi ngoài trời sớm và giữ phương án trong nhà.",
        "explanation": "Dựa trên điểm rủi ro thời tiết xác định.",
        "final_answer": "Hội An phù hợp để đi nếu bạn giữ lịch linh hoạt.",
        "llm_text_fragments": {
            "recommendation_bullets": ["Nên đi ngoài trời sớm."],
        },
    }
    client = FakeQwenClient(json.dumps(localized_json, ensure_ascii=False))
    localizer = QwenVietnameseLocalizer(client=client, model="fake-qwen", timeout_seconds=1)

    localized = asyncio.run(localizer.localize(output_fixture()))

    assert client.calls == 1
    assert localized.final_answer.startswith("Hội An")
    assert localized.risk_assessment["rain_risk"] == RiskLevel.medium
    assert localized.metadata["weather_stats"]["max_rain_prob"] == 45
    assert localized.metadata["sources_used"] == ["open_meteo", "weatherapi"]
    assert localized.metadata["response_language"] == "vi"
    assert localized.metadata["localization_source"] == "qwen_localizer"
    assert localized.metadata["llm_text_fragments"]["recommendation_bullets"][0].startswith("Nên")


def test_qwen_localizer_invalid_json_falls_back_to_original_output():
    client = FakeQwenClient("not json")
    localizer = QwenVietnameseLocalizer(client=client, model="fake-qwen", timeout_seconds=1)
    original = output_fixture()

    localized = asyncio.run(localizer.localize(original))

    assert localized.final_answer == original.final_answer
    assert localized.prediction == original.prediction
    assert localized.metadata["response_language"] == "vi"
    assert localized.metadata["localization_source"] == "fallback_original"
    assert "localization_error" in localized.metadata


def test_intelligence_service_skips_localizer_for_english_input():
    localizer = RecordingLocalizer()
    service = IntelligenceService(vietnamese_localizer=localizer)

    localized = asyncio.run(service._localize_response_if_needed(
        SimpleNamespace(raw_user_input="What is the weather around Hoi An next week?"),
        output_fixture(),
    ))

    assert localizer.calls == 0
    assert localized.final_answer == output_fixture().final_answer
    assert localized.metadata["response_language"] == "en"
    assert localized.metadata["localization_source"] == "not_required"


def test_intelligence_service_calls_localizer_for_vietnamese_input():
    localizer = RecordingLocalizer()
    service = IntelligenceService(vietnamese_localizer=localizer)

    localized = asyncio.run(service._localize_response_if_needed(
        SimpleNamespace(raw_user_input="Tuần sau Hội An thời tiết thế nào?"),
        output_fixture(),
    ))

    assert localizer.calls == 1
    assert localized.final_answer == "Câu trả lời tiếng Việt."
    assert localized.metadata["response_language"] == "vi"
