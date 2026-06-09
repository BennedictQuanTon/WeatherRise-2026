"""
LLM Parser Agent
Calls NVIDIA NIM (Nemotron Nano 8B) to convert raw user input into structured JSON.
"""
import json
import re
import os
from openai import AsyncOpenAI
from agents.parser_agent.prompts import PARSER_SYSTEM_PROMPT
from apps.api.app.schemas.context_schema import ParserOutput, GeographicalLocation, TimeRange

NIM_LLM_BASE_URL = os.getenv("NIM_LLM_BASE_URL", "http://localhost:8001/v1")
NIM_LLM_MODEL = os.getenv("NIM_LLM_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")


class LLMParser:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=NIM_LLM_BASE_URL,
            api_key="not-needed",  # NIM doesn't need an API key when self-hosted
        )
        self.model = NIM_LLM_MODEL

    async def parse(self, raw_input: str) -> ParserOutput:
        """Parse raw user input into structured ParserOutput."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": raw_input},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handles markdown code blocks if any)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group()

            data = json.loads(content)

            return ParserOutput(
                domain=data.get("domain", "unknown"),
                intent=data.get("intent", "unknown"),
                location=data.get("location"),
                geographical_location=GeographicalLocation(
                    **data.get("geographical_location", {})
                ),
                time_range=TimeRange(**data.get("time_range", {})),
                involved_context=[],  # Always empty at parse stage
                user_constraints=data.get("user_constraints", []),
                raw_user_input=raw_input,
            )

        except Exception as e:
            print(f"[Parser] Error: {e}")
            # Graceful fallback
            return ParserOutput(
                domain="unknown",
                intent="unknown",
                location=None,
                raw_user_input=raw_input,
            )
