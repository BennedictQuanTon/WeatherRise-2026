"""
NIM Prompt Builder.
Creates the message list sent to NVIDIA NIM LLM.

Important guardrails:
  - Tells NIM not to overwrite risk_assessment
  - Tells NIM not to invent weather values
  - Tells NIM to use provided evidence only
  - Tells NIM to return valid JSON only
"""

import json
from typing import Any

from .schemas import CanonicalWeatherData, PredictionResult, FullyProcessedJSON
from .prompt_templates import get_system_prompt, REQUIRED_OUTPUT_SCHEMA, VIEW_TEXT_OUTPUT_SCHEMA, HARD_RULES


class NIMPromptBuilder:
    """Builds structured prompt messages for NIM LLM from intelligence context."""

    def build_path_a_prompt(
        self,
        processed_json: FullyProcessedJSON | dict[str, Any],
        canonical_weather: CanonicalWeatherData | dict[str, Any],
        prediction_result: PredictionResult | dict[str, Any],
    ) -> list[dict[str, str]]:
        """
        Build the complete message list for NIM.

        Args:
            processed_json: FullyProcessedJSON or equivalent dict
            canonical_weather: CanonicalWeatherData or equivalent dict
            prediction_result: PredictionResult or equivalent dict

        Returns:
            List of message dicts [{"role": "system", ...}, {"role": "user", ...}]
        """
        # Extract domain for system prompt selection
        if hasattr(processed_json, "domain"):
            domain = processed_json.domain
            intent = processed_json.intent
            raw_input = processed_json.raw_user_input
            constraints = processed_json.user_constraints
            knowledge = processed_json.knowledge_context
            mcp_ctx = processed_json.mcp_context
        else:
            domain = processed_json.get("domain", "tourism")
            intent = processed_json.get("intent", "")
            raw_input = processed_json.get("raw_user_input", "")
            constraints = processed_json.get("user_constraints", [])
            knowledge = processed_json.get("knowledge_context", {})
            mcp_ctx = processed_json.get("mcp_context", {})

        # Extract prediction result
        if hasattr(prediction_result, "model_dump"):
            pred_dict = prediction_result.model_dump()
        else:
            pred_dict = prediction_result

        # Extract weather quality
        if hasattr(canonical_weather, "data_quality"):
            weather_quality = canonical_weather.data_quality
        else:
            weather_quality = canonical_weather.get("data_quality", {})

        system = get_system_prompt(domain)

        user_payload = {
            "task": "Generate a final Weatherise response for Path A.",
            "domain": domain,
            "intent": intent,
            "raw_user_input": raw_input,
            "user_constraints": constraints,
            "knowledge_context": knowledge,
            "mcp_context": mcp_ctx,
            "weather_data_quality": weather_quality,
            "prediction_engine_result": pred_dict,
            "required_output_schema": REQUIRED_OUTPUT_SCHEMA,
            "hard_rules": HARD_RULES,
        }

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]

    def build_path_b_prompt(
        self,
        processed_json: FullyProcessedJSON | dict[str, Any],
        gold_weather_decision: Any,
        prediction_result: PredictionResult | dict[str, Any],
    ) -> list[dict[str, str]]:
        """Build the final user-facing NIM prompt for Path B."""
        if hasattr(processed_json, "domain"):
            domain = processed_json.domain
            intent = processed_json.intent
            raw_input = processed_json.raw_user_input
            constraints = processed_json.user_constraints
            knowledge = processed_json.knowledge_context
            mcp_ctx = processed_json.mcp_context
        else:
            domain = processed_json.get("domain", "tourism")
            intent = processed_json.get("intent", "")
            raw_input = processed_json.get("raw_user_input", "")
            constraints = processed_json.get("user_constraints", [])
            knowledge = processed_json.get("knowledge_context", {})
            mcp_ctx = processed_json.get("mcp_context", {})

        pred_dict = prediction_result.model_dump() if hasattr(prediction_result, "model_dump") else prediction_result
        weather_dict = (
            gold_weather_decision.model_dump()
            if hasattr(gold_weather_decision, "model_dump")
            else gold_weather_decision
        )

        user_payload = {
            "task": "Generate a final Weatherise response using Path B Gold Weather Decision.",
            "llm_role": "Write user-facing wording only. Backend code will build all required frontend fields deterministically.",
            "domain": domain,
            "intent": intent,
            "raw_user_input": raw_input,
            "user_constraints": constraints,
            "knowledge_context": knowledge,
            "mcp_context": mcp_ctx,
            "gold_weather_decision": self._slim_gold(weather_dict),
            "weather_confidence": weather_dict.get("confidence") if isinstance(weather_dict, dict) else None,
            "sources_used": weather_dict.get("sources_used") if isinstance(weather_dict, dict) else [],
            "source_conflicts": (
                (weather_dict.get("comparison_matrix") or {}).get("warnings", [])
                if isinstance(weather_dict, dict)
                else []
            ),
            "prediction_engine_result": pred_dict,
            "required_output_schema": VIEW_TEXT_OUTPUT_SCHEMA,
            "hard_rules": [
                *HARD_RULES,
                "Do not invent weather values.",
                "Do not invent coordinates.",
                "Do not invent itinerary stops, dates, or map markers.",
                "Do not decide response_type, weather_view, trip_view, or any required frontend field.",
                "Do not override deterministic risk_assessment values.",
                "Mention weather confidence and source disagreement when useful.",
            ],
        }

        return [
            {"role": "system", "content": get_system_prompt(domain)},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]

    def _slim_gold(self, weather_dict: dict[str, Any]) -> dict[str, Any]:
        """Reduce token footprint by keeping only the fields NIM needs for natural language generation."""
        if not isinstance(weather_dict, dict):
            return weather_dict
            
        slim = {
            "selected_weather": weather_dict.get("selected_weather"),
            "confidence": weather_dict.get("confidence"),
            "sources_used": weather_dict.get("sources_used"),
            "sources_rejected": weather_dict.get("sources_rejected"),
        }
        
        arbiter = weather_dict.get("arbiter_decision") or {}
        if arbiter:
            slim["arbiter_decision"] = {
                "arbiter_reason": arbiter.get("arbiter_reason"),
                "risk_interpretation": arbiter.get("risk_interpretation"),
                "warnings": arbiter.get("warnings")
            }
            
        fused = weather_dict.get("fused_weather") or {}
        if fused and fused.get("fused_values"):
            slim["fused_weather"] = {"fused_values": fused.get("fused_values")}
            
        return slim
