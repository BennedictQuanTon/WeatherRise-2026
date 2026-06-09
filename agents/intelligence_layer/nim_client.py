"""
NIM Client — OpenAI-compatible client for NVIDIA NIM LLM (Nemotron Nano 8B).
"""
import os
from openai import AsyncOpenAI

NIM_LLM_BASE_URL = os.getenv("NIM_LLM_BASE_URL", "http://localhost:8001/v1")
NIM_LLM_MODEL = os.getenv("NIM_LLM_MODEL", "nvidia/llama-3.1-nemotron-nano-8b-v1")


class NIMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=NIM_LLM_BASE_URL,
            api_key="not-needed",
        )
        self.model = NIM_LLM_MODEL

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call NIM LLM and return the response text."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=2048,
        )
        return response.choices[0].message.content.strip()
