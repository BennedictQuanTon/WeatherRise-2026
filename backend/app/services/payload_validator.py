"""
Payload Validator — Phase 4 Step 4.2 (Terminal Handoff)
=======================================================
Enforces the three data-integrity rules from context_agents_flow.md Step 4.2
before the ContextAgentPayload is appended to the global LangGraph state.

Rules:
  1. Zero-Prose Cleansing: no conversational sentences in scalar string fields
  2. Exclusivity Verification: exactly one domain schema non-null, others strictly null
  3. State Transition Invalidation: payload is frozen (model_config frozen=True on schema)
"""

from __future__ import annotations

import logging
import re

from ..schemas.domain_schemas import ContextAgentPayload

logger = logging.getLogger("uvicorn.error")

# Heuristic: a "sentence" contains a verb + subject pattern and ends with punctuation.
# Any scalar field longer than 120 chars containing a period mid-string is flagged.
_PROSE_PATTERN = re.compile(
    r"[A-Z][^.!?]*[.!?]\s+[A-Z]",  # Two sentences — definitive prose signal
)
_MAX_SCALAR_LENGTH = 200  # Hard cap on any single string field


class PayloadValidationError(Exception):
    """Raised when the ContextAgentPayload fails integrity checks."""

    pass


class PayloadValidator:
    """
    Validates ContextAgentPayload instances before they are sealed into
    the LangGraph global state container.

    All three rules must pass; any violation raises PayloadValidationError.
    """

    def validate(self, payload: ContextAgentPayload) -> ContextAgentPayload:
        """
        Run all three Step 4.2 validation passes.

        Args:
            payload: The assembled ContextAgentPayload from the context agent.

        Returns:
            The same payload instance (frozen — already immutable by schema config).

        Raises:
            PayloadValidationError: On any zero-prose or exclusivity violation.
        """
        self._check_zero_prose(payload)
        self._check_exclusivity(payload)
        logger.info(
            "[VALIDATOR] Payload validated | domain=%s | status=%s",
            payload.active_domain,
            payload.execution_status,
        )
        return payload

    def _check_zero_prose(self, payload: ContextAgentPayload) -> None:
        """
        Rule 1: Scrutinize all scalar string fields across all domain schemas.
        Ensure no conversational sentences, advisory text, or descriptive filler.
        """
        active_schema = getattr(payload, payload.active_domain, None)
        if active_schema is None:
            return

        schema_dict = active_schema.model_dump()

        for field_name, value in schema_dict.items():
            if not isinstance(value, str):
                continue

            # Cap enforcement
            if len(value) > _MAX_SCALAR_LENGTH:
                raise PayloadValidationError(
                    f"Zero-prose violation: field '{field_name}' exceeds "
                    f"{_MAX_SCALAR_LENGTH} chars (length={len(value)}). "
                    "Context agents must not generate prose."
                )

            # Sentence pattern detection
            if _PROSE_PATTERN.search(value):
                raise PayloadValidationError(
                    f"Zero-prose violation: field '{field_name}' appears to contain "
                    f"conversational sentences: '{value[:80]}...'"
                )

    def _check_exclusivity(self, payload: ContextAgentPayload) -> None:
        """
        Rule 2: Exactly one domain schema must be non-null.
        The remaining two must be strictly None.
        """
        domain_fields = {
            "tourism": payload.tourism,
            "fishery": payload.fishery,
            "construction": payload.construction,
        }

        non_null = [k for k, v in domain_fields.items() if v is not None]

        if len(non_null) != 1:
            raise PayloadValidationError(
                f"Exclusivity violation: expected exactly 1 non-null domain schema, "
                f"found {len(non_null)}: {non_null}. "
                "The context agent must populate only its own domain schema."
            )

        if non_null[0] != payload.active_domain:
            raise PayloadValidationError(
                f"Exclusivity violation: active_domain='{payload.active_domain}' "
                f"but non-null schema belongs to '{non_null[0]}'."
            )


# Module-level singleton
payload_validator = PayloadValidator()
