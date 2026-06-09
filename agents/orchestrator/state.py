from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class WorkflowState:
    """LangGraph-compatible state for Weatherise pipeline."""
    raw_input: str = ""
    session_id: str = ""
    domain: str = "unknown"
    intent: str = "unknown"
    location: Optional[str] = None
    involved_context: List[str] = field(default_factory=list)
    knowledge_context: Dict[str, Any] = field(default_factory=dict)
    mcp_context: Dict[str, Any] = field(default_factory=dict)
    user_constraints: List[str] = field(default_factory=list)
    error: Optional[str] = None
    step: str = "init"
