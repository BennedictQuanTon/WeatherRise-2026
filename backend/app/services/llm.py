"""
NIM LLM Client — Phase 4 Step 2
================================
Singleton wrapper around langchain_openai.ChatOpenAI targeting the local
NVIDIA NIM inference endpoint (OpenAI-compatible API).

NIM endpoint is expected at NIM_LLM_BASE_URL (default: http://localhost:8001/v1).
Authentication uses the NGC_API_KEY.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("uvicorn.error")


class NIMClient:
    """
    Module-level singleton providing a pre-configured ChatOpenAI client
    pointed at the bare-metal NIM LLM instance on GPU 0-1.

    The client is instantiated once and reused across all discriminator calls
    to avoid repeated connection overhead.
    """

    _instance: Optional["NIMClient"] = None
    _client = None

    def __new__(cls) -> "NIMClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(self):
        """
        Return the cached ChatOpenAI client, initializing it on first call.

        Returns:
            ChatOpenAI instance configured for the NIM endpoint.
        """
        if self._client is not None:
            return self._client

        from langchain_openai import ChatOpenAI
        from ..configs.settings import settings

        logger.info(
            "[NIM_CLIENT] Initializing NIM LLM client | base_url=%s | model=%s",
            settings.NIM_LLM_BASE_URL,
            settings.NIM_LLM_MODEL,
        )

        self._client = ChatOpenAI(
            base_url=settings.NIM_LLM_BASE_URL,
            api_key=settings.NGC_API_KEY or "nim-local",  # local NIM accepts any key
            model=settings.NIM_LLM_MODEL,
            temperature=0.0,        # Deterministic output required for discriminator
            max_tokens=256,         # Discriminator output is compact JSON only
        )

        logger.info("[NIM_CLIENT] NIM LLM client ready.")
        return self._client


# Module-level singleton export
nim_client = NIMClient()
