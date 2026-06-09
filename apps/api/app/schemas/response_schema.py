from pydantic import BaseModel
from typing import Optional, Any


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    status: str  # success | error | partial
    domain: Optional[str] = None
    location: Optional[str] = None
    prediction: Optional[str] = None
    recommendation: Optional[str] = None
    risk_assessment: Optional[Any] = None
    explanation: Optional[str] = None
    final_answer: Optional[str] = None
    error: Optional[str] = None
