"""
LLM Parser Agent — V3
Calls NVIDIA NIM to convert raw user input into structured JSON.
Extracts: domain, intent, intent_subtype, trip_request, location, time_range.
"""
import json
import re
import os
from openai import AsyncOpenAI
from agents.parser_agent.prompts import PARSER_SYSTEM_PROMPT
from apps.api.app.schemas.context_schema import (
    ParserOutput, GeographicalLocation, TimeRange, TripRequest
)

PARSER_LLM_BASE_URL = os.getenv("PARSER_LLM_BASE_URL", "http://localhost:8003/v1")
PARSER_LLM_MODEL = os.getenv("PARSER_LLM_MODEL", "weatherise-parser-qwen35-27b")


class LLMParser:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=PARSER_LLM_BASE_URL,
            api_key="not-needed",
        )
        self.model = PARSER_LLM_MODEL

    async def parse(self, raw_input: str) -> ParserOutput:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": raw_input},
                ],
                temperature=0.0,
                max_tokens=1024,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            content = response.choices[0].message.content.strip()
            
            # Robust JSON extraction to handle thinking traces & multiple JSON blocks
            extracted = None
            indices = [i for i, char in enumerate(content) if char == '{']
            for idx in reversed(indices):
                sub = content[idx:].strip()
                last_brace = sub.rfind('}')
                if last_brace != -1:
                    candidate = sub[:last_brace+1]
                    try:
                        parsed_candidate = json.loads(candidate)
                        if isinstance(parsed_candidate, dict) and "domain" in parsed_candidate:
                            extracted = candidate
                            break
                    except json.JSONDecodeError:
                        continue
            
            if extracted:
                content = extracted
            else:
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    content = json_match.group()
                    
            data = json.loads(content)
            return self._build_output(data, raw_input)
        except Exception as e:
            print(f"[Parser] Error: {e}")
            return self._fallback(raw_input)

    def _build_output(self, data: dict, raw_input: str) -> ParserOutput:
        # Build TripRequest if present
        trip_request = None
        tr_data = data.get("trip_request")
        if tr_data and isinstance(tr_data, dict):
            trip_request = TripRequest(
                duration_days=tr_data.get("duration_days"),
                trip_style=tr_data.get("trip_style", "general"),
                pace=tr_data.get("pace", "balanced"),
                preferences=tr_data.get("preferences", []),
                include_restaurants=tr_data.get("include_restaurants", True),
                include_routes=tr_data.get("include_routes", True),
                include_indoor_backups=tr_data.get("include_indoor_backups", True),
                weather_aware=tr_data.get("weather_aware", True),
            )

        return ParserOutput(
            domain=data.get("domain", "unknown"),
            intent=data.get("intent", "unknown"),
            intent_subtype=data.get("intent_subtype"),
            location=data.get("location"),
            geographical_location=GeographicalLocation(
                **data.get("geographical_location", {})
            ),
            time_range=TimeRange(**data.get("time_range", {})),
            trip_request=trip_request,
            involved_context=[],
            user_constraints=data.get("user_constraints", []),
            raw_user_input=raw_input,
        )

    def _fallback(self, raw_input: str) -> ParserOutput:
        return ParserOutput(
            domain="unknown",
            intent="general_query",
            intent_subtype=None,
            location=None,
            geographical_location=GeographicalLocation(),
            time_range=TimeRange(),
            trip_request=None,
            involved_context=[],
            user_constraints=[],
            raw_user_input=raw_input,
        )
