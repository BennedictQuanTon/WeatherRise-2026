"""Qwen-powered Vietnamese localization for final user-facing responses."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any

from .nim_client import NIMClient
from .schemas import IntelligenceOutput


class QwenVietnameseLocalizer:
    """Localizes final response text to Vietnamese without changing facts."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        enabled: bool | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.enabled = _env_bool("QWEN_LOCALIZER_ENABLED", True) if enabled is None else enabled
        self.base_url = base_url or os.getenv(
            "QWEN_LOCALIZER_BASE_URL",
            os.getenv("PARSER_LLM_BASE_URL", "http://localhost:8003/v1"),
        )
        self.model = model or os.getenv(
            "QWEN_LOCALIZER_MODEL",
            os.getenv("PARSER_LLM_MODEL", "weatherise-parser-qwen35-27b"),
        )
        self.timeout_seconds = timeout_seconds or float(os.getenv("QWEN_LOCALIZER_TIMEOUT_SECONDS", "20"))
        self.client = client or NIMClient(
            base_url=self.base_url,
            model=self.model,
            temperature=0.0,
            max_tokens=int(os.getenv("QWEN_LOCALIZER_MAX_TOKENS", "2048")),
        )

    async def localize(self, output: IntelligenceOutput) -> IntelligenceOutput:
        if not self.enabled:
            return self._fallback(output, "Qwen Vietnamese localizer is disabled.")

        start = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                self.client.chat(self._messages(output)),
                timeout=self.timeout_seconds,
            )
            latency_ms = response.latency_ms
            if latency_ms is None:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
            if response.error:
                return self._fallback(output, response.error, latency_ms=latency_ms)

            parsed = _parse_json_content(response.content)
            if not parsed:
                return self._fallback(output, "Qwen localizer returned invalid JSON.", latency_ms=latency_ms)

            return self._localized_output(output, parsed, latency_ms=latency_ms)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return self._fallback(output, str(exc), latency_ms=latency_ms)

    def _messages(self, output: IntelligenceOutput) -> list[dict[str, str]]:
        payload = {
            "task": "Localize the final Weatherise response to Vietnamese.",
            "response_contract": {
                "prediction": output.prediction,
                "recommendation": output.recommendation,
                "explanation": output.explanation,
                "final_answer": output.final_answer,
                "llm_text_fragments": output.metadata.get("llm_text_fragments", {}),
            },
            "immutable_context": {
                "risk_assessment": {
                    key: value.value if hasattr(value, "value") else value
                    for key, value in output.risk_assessment.items()
                },
                "weather_stats": output.metadata.get("weather_stats", {}),
                "evidence": output.metadata.get("evidence", []),
                "weather_path": output.metadata.get("weather_path"),
                "weather_confidence": output.metadata.get("weather_confidence"),
                "weather_mode": output.metadata.get("weather_mode"),
                "sources_used": output.metadata.get("sources_used", []),
                "sources_rejected": output.metadata.get("sources_rejected", []),
            },
            "required_output_schema": {
                "prediction": "Vietnamese string",
                "recommendation": "Vietnamese string",
                "explanation": "Vietnamese string",
                "final_answer": "Vietnamese string",
                "llm_text_fragments": "optional object with translated natural-language strings only",
            },
            "hard_rules": [
                "Return valid JSON only.",
                "Do not change JSON keys.",
                "Do not add new facts, weather warnings, official alerts, places, restaurants, or assumptions.",
                "Preserve all weather values, dates, coordinates, risk levels, source names, and recommendations.",
                "Keep numbers, units, percentages, and place names unchanged.",
                "Translate natural-language display strings only.",
                "Keep risk enums and metadata semantics unchanged.",
            ],
        }
        return [
            {
                "role": "system",
                "content": (
                    "You are a Vietnamese localization editor for Weatherise. "
                    "You convert final user-facing response text into natural Vietnamese while preserving facts. "
                    "You never alter structured values, risk scores, weather data, source names, or JSON keys."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ]

    def _localized_output(
        self,
        output: IntelligenceOutput,
        parsed: dict[str, Any],
        *,
        latency_ms: float,
    ) -> IntelligenceOutput:
        metadata = dict(output.metadata)
        metadata.update({
            "response_language": "vi",
            "localization_model": self.model,
            "localization_source": "qwen_localizer",
            "localization_latency_ms": latency_ms,
        })
        localized_fragments = _sanitize_text_fragments(parsed.get("llm_text_fragments"))
        if localized_fragments:
            metadata["llm_text_fragments"] = localized_fragments

        return output.model_copy(update={
            "prediction": _string_or_original(parsed.get("prediction"), output.prediction),
            "recommendation": _string_or_original(parsed.get("recommendation"), output.recommendation),
            "explanation": _string_or_original(parsed.get("explanation"), output.explanation),
            "final_answer": _string_or_original(parsed.get("final_answer"), output.final_answer),
            "metadata": metadata,
        })

    def _fallback(
        self,
        output: IntelligenceOutput,
        error: str,
        *,
        latency_ms: float | None = None,
    ) -> IntelligenceOutput:
        metadata = dict(output.metadata)
        metadata.update({
            "response_language": "vi",
            "localization_model": self.model,
            "localization_source": "fallback_original",
            "localization_error": error,
        })
        if latency_ms is not None:
            metadata["localization_latency_ms"] = latency_ms
        return output.model_copy(update={"metadata": metadata})


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_json_content(content: str) -> dict[str, Any]:
    if not content:
        return {}
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        pass

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").replace("json\n", "", 1).replace("JSON\n", "", 1)
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            pass

    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _sanitize_text_fragments(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    sanitized: dict[str, Any] = {}
    if isinstance(value.get("assumption_summary"), str):
        sanitized["assumption_summary"] = value["assumption_summary"]
    if isinstance(value.get("recommendation_bullets"), list):
        bullets = [item for item in value["recommendation_bullets"] if isinstance(item, str)]
        if bullets:
            sanitized["recommendation_bullets"] = bullets
    if isinstance(value.get("insight_bullets"), list):
        insights = []
        for item in value["insight_bullets"]:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            body = item.get("body")
            if isinstance(title, str) and isinstance(body, str):
                insights.append({
                    "title": title,
                    "body": body,
                    "type": item.get("type") if item.get("type") in {"rain", "wind", "heat", "travel", "general"} else "general",
                })
        if insights:
            sanitized["insight_bullets"] = insights
    if isinstance(value.get("trip_day_summaries"), list):
        summaries = []
        for item in value["trip_day_summaries"]:
            if isinstance(item, dict) and isinstance(item.get("summary"), str):
                summaries.append({"day": item.get("day"), "summary": item["summary"]})
        if summaries:
            sanitized["trip_day_summaries"] = summaries
    return sanitized


def _string_or_original(value: Any, original: str) -> str:
    return value if isinstance(value, str) and value.strip() else original
