"""
NIM Client — OpenAI-compatible client for NVIDIA NIM LLM.
Uses the openai Python library with latency tracking.
"""

import os
import time
from typing import Any

from openai import AsyncOpenAI

from .schemas import NIMResponse


class NIMClient:
    """
    Async client for NVIDIA NIM LLM using the OpenAI-compatible API.
    Tracks latency and returns structured NIMResponse.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ):
        self.base_url = base_url or os.getenv(
            "NIM_LLM_BASE_URL",
            os.getenv("NIM_BASE_URL", "http://localhost:8001/v1"),
        )
        self.model = model or os.getenv(
            "NIM_LLM_MODEL",
            os.getenv("NIM_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1"),
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=os.getenv("NIM_API_KEY", "not-needed"),
        )

    async def chat(self, messages: list[dict[str, str]]) -> NIMResponse:
        """
        Send messages to NIM and return structured NIMResponse.

        Args:
            messages: list of {"role": str, "content": str}

        Returns:
            NIMResponse with model name, content, usage, latency, and error info.
        """
        start = time.perf_counter()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            # Extract usage info
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return NIMResponse(
                model=self.model,
                content=response.choices[0].message.content.strip(),
                raw=response.model_dump() if hasattr(response, "model_dump") else {},
                usage=usage,
                latency_ms=latency_ms,
                error=None,
            )

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return NIMResponse(
                model=self.model,
                content="",
                raw={},
                usage={},
                latency_ms=latency_ms,
                error=str(exc),
            )
