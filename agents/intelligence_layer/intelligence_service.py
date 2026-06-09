"""
Intelligence Service — Orchestrates the full Path A pipeline.

Flow:
  1. Validate input
  2. Fetch weather from Open-Meteo (Intelligence Layer owns weather fetching)
  3. Normalize into Canonical Weather JSON
  4. Run Prediction Engine (deterministic risk scoring)
  5. Build NIM prompt
  6. Call NIM LLM
  7. Build final response

Error handling:
  - Weather fetch fails → empty canonical (prediction defaults to "medium")
  - NIM call fails → response_builder uses prediction engine fallback text
  - Never crashes the pipeline
"""

import traceback
from typing import Any

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
    ):
        self.weather_provider = weather_provider or OpenMeteoProvider()
        self.weather_adapter = weather_adapter or OpenMeteoAdapter()
        self.weather_normalizer = weather_normalizer or WeatherNormalizer()
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.prompt_builder = prompt_builder or NIMPromptBuilder()
        self.nim_client = nim_client or NIMClient()
        self.response_builder = response_builder or ResponseBuilder()

    async def process(self, processed_json: FullyProcessedJSON) -> IntelligenceOutput:
        """
        Run the full Path A pipeline.

        Args:
            processed_json: Fully processed input from Context Agent.

        Returns:
            IntelligenceOutput with prediction, recommendation, risk, explanation.
        """
        # 1. Build weather fetch request
        coords = processed_json.geographical_location.coordinates
        request = {
            "latitude": coords.latitude,
            "longitude": coords.longitude,
            "timezone": processed_json.time_range.timezone,
            "forecast_days": 7,
        }

        # 2. Fetch weather (Intelligence Layer owns this)
        canonical_weather = await self._fetch_and_normalize_weather(
            request, processed_json
        )

        # 3. Run prediction engine (deterministic)
        prediction = self.prediction_engine.predict(processed_json, canonical_weather)

        # 4. Build NIM prompt
        messages = self.prompt_builder.build_path_a_prompt(
            processed_json, canonical_weather, prediction
        )

        # 5. Call NIM LLM
        nim_response = await self.nim_client.chat(messages)

        # 6. Build final response
        return self.response_builder.build(prediction, nim_response)

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

            fp = FullyProcessedJSON(
                domain=payload_dict.get("domain", "tourism"),
                intent=payload_dict.get("intent", "general"),
                location=payload_dict.get("location"),
                geographical_location={
                    "country": geo.get("country"),
                    "city": geo.get("city"),
                    "coordinates": coords,
                },
                time_range=payload_dict.get("time_range", {
                    "start": "2026-06-15",
                    "end": "2026-06-17",
                    "timezone": "Asia/Ho_Chi_Minh",
                }),
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
