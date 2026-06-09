"""
Chat Request Schema — Phase 4 API Entry Point
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Inbound payload for POST /chat.
    The raw user_message is the string token that enters the GR-In gate.
    """

    user_message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Raw natural language input from the end user",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        description="Client-generated session identifier for state continuity",
    )
