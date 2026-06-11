"""
Intelligence Service — Orchestrates the Path B weather intelligence pipeline.

Flow:
  1. Validate input
  2. Build Path B Gold Weather Decision from multi-source evidence
  3. Run Prediction Engine (deterministic risk scoring)
  4. Build final NIM prompt
  5. Call NIM LLM
  6. Build final response

Error handling:
  - Provider failures are isolated inside Path B
  - NIM call fails → response_builder uses prediction engine fallback text
  - Never crashes the pipeline
"""

import traceback
import time
from typing import Any

from apps.api.app.routes.monitor import emit

from .schemas import (
    FullyProcessedJSON,
    CanonicalWeatherData,
    CanonicalWeatherPoint,
    IntelligenceOutput,
    NIMResponse,
    RiskLevel,
)
from .weather_providers.open_meteo_provider import OpenMeteoProvider
from .adapters.open_meteo_adapter import OpenMeteoAdapter
from .weather_normalizer import WeatherNormalizer
from .prediction_engine import PredictionEngine
from .prompt_builder import NIMPromptBuilder
from .nim_client import NIMClient
from .response_builder import ResponseBuilder
from .language_detection import detect_response_language
from .vietnamese_localizer import QwenVietnameseLocalizer
from .weather_path_b.gold_weather_decision import build_weather_debug
from .weather_path_b.path_b_service import PathBWeatherService


class IntelligenceService:
    """
    Main entry point for the Intelligence Layer.
    Orchestrates weather fetching, normalization, prediction, NIM reasoning,
    and response building.
    """

    def __init__(
        self,
        weather_provider: Any | None = None,
        weather_adapter: Any | None = None,
        weather_normalizer: Any | None = None,
        prediction_engine: Any | None = None,
        prompt_builder: Any | None = None,
        nim_client: Any | None = None,
        response_builder: Any | None = None,
        path_b_service: Any | None = None,
        vietnamese_localizer: Any | None = None,
    ):
        self.weather_provider = weather_provider or OpenMeteoProvider()
        self.weather_adapter = weather_adapter or OpenMeteoAdapter()
        self.weather_normalizer = weather_normalizer or WeatherNormalizer()
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.prompt_builder = prompt_builder or NIMPromptBuilder()
        self.nim_client = nim_client or NIMClient()
        self.response_builder = response_builder or ResponseBuilder()
        self.path_b_service = path_b_service or PathBWeatherService()
        self.vietnamese_localizer = vietnamese_localizer or QwenVietnameseLocalizer()

    async def process(self, processed_json: FullyProcessedJSON) -> IntelligenceOutput:
        """
        Run the full Path B pipeline.

        Args:
            processed_json: Fully processed input from Context Agent.

        Returns:
            IntelligenceOutput with prediction, recommendation, risk, explanation.
        """
        try:
            t_path_b = time.time()
            gold_weather_decision = await self.path_b_service.run(processed_json)
            ms_path_b = int((time.time() - t_path_b) * 1000)
            emit("step", "Intelligence", "Path B Weather Consensus", duration_ms=ms_path_b)
        except Exception as exc:
            print(f"[Intelligence] Path B failed: {exc}")
            traceback.print_exc()
            return IntelligenceOutput(
                prediction="Unable to process weather intelligence.",
                recommendation="Please try again later or use a more specific location and time.",
                risk_assessment={"overall_risk": RiskLevel.medium},
                explanation=f"Path B weather intelligence failed: {exc}",
                final_answer="Weather intelligence is temporarily unavailable. Please try again.",
                metadata={"error": str(exc), "weather_path": "path_b", "weather_mode": "weather_unavailable"},
            )

        # 3. Run prediction engine (deterministic)
        t_pred = time.time()
        prediction = self.prediction_engine.predict(processed_json, gold_weather_decision)
        ms_pred = int((time.time() - t_pred) * 1000)
        emit("step", "Intelligence", "Prediction Engine Risk Scoring", duration_ms=ms_pred)

        # 4. Build NIM prompt
        t_prompt = time.time()
        messages = self.prompt_builder.build_path_b_prompt(
            processed_json, gold_weather_decision, prediction
        )
        ms_prompt = int((time.time() - t_prompt) * 1000)
        emit("step", "Intelligence", "Prompt Building", duration_ms=ms_prompt)

        # 5. Call NIM LLM
        t_nim = time.time()
        nim_response = await self.nim_client.chat(messages)
        ms_nim = int((time.time() - t_nim) * 1000)
        emit("step", "Intelligence", "NIM LLM Reasoning Call", duration_ms=ms_nim)

        # 6. Build final response
        response = self.response_builder.build(
            prediction,
            nim_response,
            extra_metadata=self._path_b_metadata(gold_weather_decision),
        )
        return await self._localize_response_if_needed(processed_json, response)

    async def _localize_response_if_needed(
        self,
        processed_json: Any,
        response: IntelligenceOutput,
    ) -> IntelligenceOutput:
        raw_user_input = getattr(processed_json, "raw_user_input", None)
        response_language = detect_response_language(raw_user_input)
        if response_language != "vi":
            metadata = dict(response.metadata)
            metadata.setdefault("response_language", "en")
            metadata.setdefault("localization_source", "not_required")
            return response.model_copy(update={"metadata": metadata})

        emit("step", "Intelligence", "Qwen Vietnamese Localization")
        return await self.vietnamese_localizer.localize(response)

    def _path_b_metadata(self, gold_weather_decision: Any) -> dict[str, Any]:
        debug = build_weather_debug(gold_weather_decision)
        return {
            "weather_path": "path_b",
            "weather_confidence": gold_weather_decision.confidence,
            "weather_mode": gold_weather_decision.selected_mode,
            "sources_used": gold_weather_decision.sources_used,
            "sources_rejected": gold_weather_decision.sources_rejected,
            "weather_debug": debug,
        }

    async def _fetch_and_normalize_weather(
        self,
        request: dict[str, Any],
        processed_json: FullyProcessedJSON,
    ) -> CanonicalWeatherData:
        """Fetch weather from Open-Meteo and normalize to canonical format."""
        try:
            raw_bundle = await self.weather_provider.fetch(request)

            context = {
                "location": {
                    "name": processed_json.location or "Unknown",
                    "latitude": request["latitude"],
                    "longitude": request["longitude"],
                    "timezone": request["timezone"],
                },
                "forecast_window": {
                    "start": processed_json.time_range.start,
                    "end": processed_json.time_range.end,
                },
            }

            return self.weather_normalizer.normalize(raw_bundle, context)

        except Exception as exc:
            print(f"[Intelligence] Weather fetch failed: {exc}")
            traceback.print_exc()
            # Return empty canonical — prediction engine will default to "medium"
            return self._empty_canonical(request, processed_json)

    def _empty_canonical(
        self,
        request: dict[str, Any],
        processed_json: FullyProcessedJSON,
    ) -> CanonicalWeatherData:
        """Create an empty canonical weather data when fetch fails."""
        return CanonicalWeatherData(
            source="none",
            source_type="fallback",
            location={
                "name": processed_json.location or "Unknown",
                "latitude": request["latitude"],
                "longitude": request["longitude"],
                "timezone": request["timezone"],
            },
            forecast_window={
                "start": processed_json.time_range.start,
                "end": processed_json.time_range.end,
            },
            resolution={"temporal": "none", "spatial": "none"},
            variables=[],
            data_quality={
                "missing_fields": ["all"],
                "confidence": "none",
                "notes": ["Weather data unavailable. Using fallback defaults."],
            },
        )

    # ── Backwards-compatible wrapper for pipeline_service.py ──

    async def reason(self, payload: Any) -> IntelligenceOutput:
        """
        Backwards-compatible entry point called by pipeline_service.py.
        Accepts a FullyProcessedPayload from apps.api and converts it.
        """
        # If already a FullyProcessedJSON, just use it
        if isinstance(payload, FullyProcessedJSON):
            return await self.process(payload)

        # Convert from FullyProcessedPayload (apps.api schema) to our internal schema
        try:
            payload_dict = payload.model_dump() if hasattr(payload, "model_dump") else payload

            # Ensure coordinates exist
            geo = payload_dict.get("geographical_location", {})
            coords = geo.get("coordinates")
            if not coords:
                coords = {"latitude": 16.0544, "longitude": 108.2022}

            tr = payload_dict.get("time_range", {}) or {}
            tr_start = tr.get("start")
            tr_end = tr.get("end")
            if not tr_start or not tr_end:
                from datetime import datetime, timedelta
                now = datetime.now()
                tr_start = tr_start or now.strftime("%Y-%m-%d")
                tr_end = tr_end or (now + timedelta(days=3)).strftime("%Y-%m-%d")

            fp = FullyProcessedJSON(
                domain=payload_dict.get("domain", "tourism"),
                intent=payload_dict.get("intent", "general"),
                location=payload_dict.get("location"),
                geographical_location={
                    "country": geo.get("country"),
                    "city": geo.get("city"),
                    "coordinates": coords,
                },
                time_range={
                    "raw_text": tr.get("raw_text"),
                    "start": tr_start,
                    "end": tr_end,
                    "timezone": tr.get("timezone") or "Asia/Ho_Chi_Minh",
                },
                involved_context=payload_dict.get("involved_context", []),
                knowledge_context=self._extract_knowledge_context(payload_dict),
                mcp_context=self._extract_mcp_context(payload_dict),
                intelligence_requirements=payload_dict.get("intelligence_requirements", {
                    "realtime_weather_needed": True,
                    "weather_variables": [],
                    "reasoning_task": "general_weather_advice",
                }),
                user_constraints=payload_dict.get("user_constraints", []),
                raw_user_input=payload_dict.get("raw_user_input", ""),
            )

            return await self.process(fp)

        except Exception as exc:
            print(f"[Intelligence] Conversion error: {exc}")
            traceback.print_exc()
            # Return a minimal error output
            return IntelligenceOutput(
                prediction="Unable to process weather intelligence.",
                recommendation="Please try again with more specific location and time details.",
                risk_assessment={"overall_risk": RiskLevel.medium},
                explanation=f"Error during processing: {exc}",
                final_answer="Weather intelligence is temporarily unavailable. Please try again.",
                metadata={"error": str(exc)},
            )

    def _extract_knowledge_context(self, payload_dict: dict) -> dict:
        """Extract knowledge context from payload, handling nested structures."""
        kc = payload_dict.get("knowledge_context", {})
        if isinstance(kc, dict):
            return kc.get("found_context", kc) if "found_context" in kc else kc
        return {}

    def _extract_mcp_context(self, payload_dict: dict) -> dict:
        """Extract MCP context from payload, converting to flat dict."""
        mc = payload_dict.get("mcp_context", {})
        if isinstance(mc, dict):
            return mc
        if hasattr(mc, "model_dump"):
            return mc.model_dump()
        return {}
