"""NIM Weather Arbiter for Path B evidence decisions."""

from __future__ import annotations

import json
import os
from typing import Any

from agents.intelligence_layer.nim_client import NIMClient

from .schemas import (
    ArbiterDecision,
    Earth2ProcessingReport,
    FusedWeather,
    QualityReport,
    SourceComparisonMatrix,
    SourceScore,
    WeatherRequirement,
)


ARBITER_SYSTEM_PROMPT = """You are the Weatherise NIM Weather Arbiter.

You receive structured weather evidence from multiple providers, source quality
scores, source ranking reports, a source comparison matrix, fused weather
values, Earth2Studio processing reports, user/domain context, and retrieved
weather-risk knowledge.

Your job:
1. Decide whether to trust fused_weather, a best single source, conservative risk interpretation, latest snapshot, or degraded baseline.
2. Explain source conflicts clearly.
3. Explain why a source is trusted or weakened.
4. Return confidence and warnings.
5. Return valid JSON only.

Hard rules:
- Do not invent weather values.
- Do not change numeric weather values unless the provided fused_weather already contains them.
- Do not use rejected sources as trusted evidence.
- Do not ignore quality_report warnings.
- Do not claim exact micro-weather certainty.
- If sources disagree and the task is safety-sensitive, prefer conservative interpretation.
"""


class NIMWeatherArbiter:
    """Structured arbiter with deterministic fallback."""

    def __init__(self, enabled: bool | None = None, nim_client: NIMClient | None = None):
        if enabled is None:
            enabled = os.getenv("NIM_WEATHER_ARBITER_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
        self.enabled = enabled
        self.nim_client = nim_client or NIMClient(
            model=os.getenv("NIM_WEATHER_ARBITER_MODEL") or None,
            temperature=0.0,
            max_tokens=768,
        )

    async def decide(
        self,
        requirement: WeatherRequirement,
        source_scores: list[SourceScore],
        quality_reports: list[QualityReport],
        comparison_matrix: SourceComparisonMatrix,
        fused_weather: FusedWeather,
        earth2_report: Earth2ProcessingReport,
        retrieved_weather_knowledge: list[dict[str, Any]],
    ) -> ArbiterDecision:
        if not self.enabled:
            return self._fallback(fused_weather, source_scores, quality_reports, "NIM Weather Arbiter disabled by config.")

        from agents.cache_client import get_cache_client
        cache = get_cache_client()
        lat = round(requirement.latitude, 2) if requirement.latitude else 0
        lon = round(requirement.longitude, 2) if requirement.longitude else 0
        source_str = "-".join(sorted([s.source_code for s in source_scores]))
        cache_key = cache.generate_key("arbiter", lat, lon, requirement.domain, requirement.start_date, source_str)
        
        cached_data = await cache.get(cache_key)
        if cached_data:
            try:
                return ArbiterDecision(**cached_data)
            except Exception:
                pass

        messages = self._messages(
            requirement,
            source_scores,
            quality_reports,
            comparison_matrix,
            fused_weather,
            earth2_report,
            retrieved_weather_knowledge,
        )
        response = await self.nim_client.chat(messages)
        decision = self._parse_decision(response.content)
        if decision:
            await cache.set(cache_key, decision.model_dump(), ttl_seconds=900)
            return decision

        retry_messages = [
            *messages,
            {
                "role": "user",
                "content": "Your previous response was invalid. Return only valid JSON matching the requested schema.",
            },
        ]
        retry = await self.nim_client.chat(retry_messages)
        decision = self._parse_decision(retry.content)
        if decision:
            await cache.set(cache_key, decision.model_dump(), ttl_seconds=900)
            return decision

        return self._fallback(
            fused_weather,
            source_scores,
            quality_reports,
            f"NIM arbiter fallback used. First error={response.error}; retry error={retry.error}",
        )

    def _messages(
        self,
        requirement: WeatherRequirement,
        source_scores: list[SourceScore],
        quality_reports: list[QualityReport],
        comparison_matrix: SourceComparisonMatrix,
        fused_weather: FusedWeather,
        earth2_report: Earth2ProcessingReport,
        retrieved_weather_knowledge: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        payload = {
            "task": "weather_evidence_arbitration",
            "domain": requirement.domain,
            "activity_type": requirement.activity_type,
            "user_constraints": requirement.user_constraints,
            "required_variables": requirement.required_variables,
            "safety_mode": requirement.safety_mode,
            "source_rankings": [score.model_dump() for score in source_scores],
            "quality_reports": [report.model_dump() for report in quality_reports],
            "source_comparison_matrix": comparison_matrix.model_dump(),
            "fused_weather": fused_weather.model_dump(),
            "earth2_processing_report": earth2_report.model_dump(),
            "retrieved_weather_knowledge": retrieved_weather_knowledge,
            "return_only_json_shape": {
                "selected_weather_mode": "fused_weather | best_single_source | conservative_risk | latest_snapshot | degraded_open_meteo_only",
                "best_individual_source": "string or null",
                "confidence": 0.0,
                "arbiter_reason": "string",
                "risk_interpretation": "string",
                "warnings": [],
            },
        }
        return [
            {"role": "system", "content": ARBITER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ]

    def _parse_decision(self, content: str) -> ArbiterDecision | None:
        if not content:
            return None
        candidates = [content.strip()]
        if "```" in content:
            stripped = content.strip().strip("`").replace("json\n", "", 1).replace("JSON\n", "", 1)
            candidates.append(stripped)
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(content[start : end + 1])
        for candidate in candidates:
            try:
                return ArbiterDecision(**json.loads(candidate))
            except Exception:
                continue
        return None

    def _fallback(
        self,
        fused_weather: FusedWeather,
        source_scores: list[SourceScore],
        quality_reports: list[QualityReport],
        reason: str,
    ) -> ArbiterDecision:
        valid_reports = [report for report in quality_reports if report.valid]
        best_source = source_scores[0].source_code if source_scores else None
        if fused_weather.confidence >= 0.7 and fused_weather.fused_values:
            mode = "fused_weather"
        elif best_source:
            mode = "best_single_source"
        elif any(report.source_code == "open_meteo" for report in valid_reports):
            mode = "degraded_open_meteo_only"
            best_source = "open_meteo"
        else:
            mode = "weather_unavailable"
        return ArbiterDecision(
            selected_weather_mode=mode,
            best_individual_source=best_source,
            confidence=fused_weather.confidence if mode == "fused_weather" else max(0.25, fused_weather.confidence * 0.8),
            arbiter_reason=reason,
            risk_interpretation="Use deterministic fused/selected weather evidence with conservative handling when confidence is reduced.",
            warnings=["Deterministic arbiter fallback used."],
        )
