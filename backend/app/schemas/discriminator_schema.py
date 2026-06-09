"""
Discriminator Routing Matrix — Phase 4 Step 2
=============================================
Structured output schema enforced directly by the NIM LLM.
The model's top-k parameters are forced to resolve exactly one primary_intent string.
Secondary intents are explicitly truncated from the output state.
"""

from typing import Literal
from pydantic import BaseModel, Field


class DiscriminatorRoutingMatrix(BaseModel):
    """
    JSON-schema-forced output model for the Discriminator node.
    Bound to the NIM LLM via .with_structured_output() to guarantee
    schema compliance on every inference call.
    """

    primary_intent: Literal["tourism", "fishery", "construction", "REJECT_OUT_OF_SCOPE"] = Field(
        ...,
        description=(
            "Exactly one resolved domain intent. Must be one of the four certified "
            "enterprise domains or REJECT_OUT_OF_SCOPE if the query does not match "
            "any domain. No secondary intents are permitted."
        ),
    )

    routing_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Model confidence score for the primary_intent classification. "
            "Values below 0.70 will bypass all context agents and route directly "
            "to the terminal error handler."
        ),
    )

    extraction_key: str = Field(
        ...,
        min_length=1,
        description=(
            "Isolated entity parameter from the token stream. "
            "Examples: a localized site index, a coordinate string, "
            "a place name, a port identifier, or a construction site code."
        ),
    )
