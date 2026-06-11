"""
Response Builder — Assembles the final IntelligenceOutput.

Critical design rule:
  risk_assessment ALWAYS comes from PredictionEngine, NEVER from NIM.
  NIM provides natural language (prediction, recommendation, explanation, final_answer).
  If NIM fails or returns invalid JSON, PredictionEngine summaries are used as fallback.
"""

import json
from typing import Any

from .schemas import PredictionResult, NIMResponse, IntelligenceOutput, RiskLevel


class ResponseBuilder:
    """Builds final output and protects deterministic risk scores."""

    def build(
        self,
        prediction_result: PredictionResult,
        nim_response: NIMResponse,
        extra_metadata: dict[str, Any] | None = None,
    ) -> IntelligenceOutput:
        """
        Merge prediction engine result with NIM LLM output.

        Args:
            prediction_result: Deterministic risk scoring output
            nim_response: NIM LLM response (may contain errors)

        Returns:
            IntelligenceOutput with deterministic risk + LLM natural language.
        """
        llm_json = self._parse_nim_content(nim_response.content)

        # Natural language from NIM, or fallback to prediction engine summaries
        prediction = llm_json.get("prediction", prediction_result.prediction_summary)
        recommendation = llm_json.get("recommendation", prediction_result.recommendation_summary)
        explanation = llm_json.get(
            "explanation",
            "Generated from deterministic weather risk scoring.",
        )
        final_answer = llm_json.get(
            "final_answer",
            prediction_result.recommendation_summary,
        )

        # Metadata for debugging and monitoring
        metadata: dict[str, Any] = {
            "model": nim_response.model,
            "latency_ms": nim_response.latency_ms,
            "risk_source": "prediction_engine",
            "llm_source": "nvidia_nim" if not nim_response.error else "fallback",
            "llm_json_valid": bool(llm_json),
            "evidence": prediction_result.evidence,
            "weather_stats": prediction_result.weather_stats,
        }

        if nim_response.error:
            metadata["llm_error"] = nim_response.error

        if nim_response.usage:
            metadata["token_usage"] = nim_response.usage

        if extra_metadata:
            metadata.update(extra_metadata)

        return IntelligenceOutput(
            prediction=prediction,
            recommendation=recommendation,
            risk_assessment=prediction_result.risk_assessment,  # ALWAYS from engine
            explanation=explanation,
            final_answer=final_answer,
            metadata=metadata,
        )

    def _parse_nim_content(self, content: str) -> dict[str, Any]:
        """
        Try to parse NIM response content as JSON.
        Handles common model behaviors like wrapping JSON in code fences.
        """
        if not content:
            return {}

        # Direct JSON parse
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Handle code-fenced JSON (```json ... ```)
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            stripped = stripped.replace("json\n", "", 1).replace("JSON\n", "", 1)
            try:
                return json.loads(stripped)
            except (json.JSONDecodeError, TypeError):
                pass

        # Try to extract JSON object from mixed content
        import re
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except (json.JSONDecodeError, TypeError):
                pass

        return {}
