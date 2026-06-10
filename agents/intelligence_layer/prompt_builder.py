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
from .prompt_templates import get_system_prompt, REQUIRED_OUTPUT_SCHEMA, HARD_RULES


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
        else:
            domain = processed_json.get("domain", "tourism")
            intent = processed_json.get("intent", "")
            raw_input = processed_json.get("raw_user_input", "")
            constraints = processed_json.get("user_constraints", [])
            knowledge = processed_json.get("knowledge_context", {})

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
            "weather_data_quality": weather_quality,
            "prediction_engine_result": pred_dict,
            "required_output_schema": REQUIRED_OUTPUT_SCHEMA,
            "hard_rules": HARD_RULES,
        }

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]
