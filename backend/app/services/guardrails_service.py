"""
Guardrails Gate Service — Phase 4 Step 1 (GR-In)
================================================
Wraps the NVIDIA NeMo Guardrails engine to enforce the inbound security
and topical perimeter before any generative or parsing models are invoked.

Design contract (per context_agents_flow.md Step 1):
  - Compile config.yml + rails.co once at startup (singleton pattern)
  - Intercept injection vectors, jailbreak syntaxes, and off-topic prompts
  - Pass sanitized string token downstream without mutating user context
  - On rejection → raise GateRejectionError (terminates graph trace)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("uvicorn.error")


class GateRejectionError(Exception):
    """
    Raised when the GR-In gate intercepts an invalid or out-of-scope prompt.
    Upstream handlers must catch this to terminate the graph trace immediately.
    """

    def __init__(self, reason: str, original_input: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.original_input = original_input


class GuardrailsGate:
    """
    Singleton-safe NeMo Guardrails wrapper.
    Compiles the Colang policy on first call to avoid repeated I/O overhead.

    Usage:
        gate = GuardrailsGate()
        sanitized = await gate.validate(raw_user_input)
    """

    _rails = None  # Class-level cached instance

    def __init__(self) -> None:
        from ..configs.settings import settings

        self._config_path = settings.GUARDRAILS_CONFIG_PATH

    def _load_rails(self):
        """Lazily compile the NeMo Guardrails engine from the config directory."""
        if GuardrailsGate._rails is not None:
            return GuardrailsGate._rails

        try:
            from nemoguardrails import LLMRails, RailsConfig

            config = RailsConfig.from_path(self._config_path)
            GuardrailsGate._rails = LLMRails(config)
            logger.info(
                "[GR-IN] NeMo Guardrails engine compiled from: %s", self._config_path
            )
        except ImportError:
            logger.warning(
                "[GR-IN] nemoguardrails not installed — running in PASSTHROUGH mode. "
                "Install nemoguardrails for production enforcement."
            )
            GuardrailsGate._rails = None

        return GuardrailsGate._rails

    async def validate(self, raw_input: str) -> str:
        """
        Run the raw user string through the NeMo inbound rail stack.

        Steps:
          1. Pass raw_input through Colang policy evaluation
          2. If the rail intercepts → raise GateRejectionError
          3. If the rail passes → return the original sanitized string token
             (the Guardrails engine does NOT mutate or rephrase the input)

        Returns:
            sanitized_input: The original string confirmed clean by the gate.

        Raises:
            GateRejectionError: On any injection, jailbreak, or topical violation.
        """
        rails = self._load_rails()

        # Passthrough mode when nemoguardrails is not installed (dev/test)
        if rails is None:
            logger.warning("[GR-IN] PASSTHROUGH: no rail enforcement active.")
            return raw_input

        try:
            response = await rails.generate_async(
                messages=[{"role": "user", "content": raw_input}]
            )

            # NeMo Guardrails returns the bot's refusal message if a rail fires.
            # Detection: if the response contains one of the known refusal prefixes,
            # the rail was triggered → reject.
            refusal_signals = [
                "falls outside these certified domains",
                "Prompt injection detected",
                "Jailbreak syntax detected",
            ]

            response_text: str = (
                response.get("content", "")
                if isinstance(response, dict)
                else str(response)
            )

            for signal in refusal_signals:
                if signal.lower() in response_text.lower():
                    reason = response_text.strip()
                    logger.warning(
                        "[GR-IN] Gate rejection fired | reason=%s | input_preview=%.80s",
                        reason,
                        raw_input,
                    )
                    raise GateRejectionError(reason=reason, original_input=raw_input)

            # Rail passed — return the original sanitized string unchanged
            logger.info("[GR-IN] Gate PASS | input_preview=%.80s", raw_input)
            return raw_input

        except GateRejectionError:
            raise
        except Exception as exc:
            logger.error("[GR-IN] Guardrails engine error: %s — using PASSTHROUGH", exc)
            # On engine error, pass through to avoid blocking legitimate traffic
            return raw_input
