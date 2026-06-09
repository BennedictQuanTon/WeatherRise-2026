from pydantic import BaseModel
from typing import Any, Optional, Dict

class StandardResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, str]] = None
    meta: Optional[Dict[str, Any]] = None

def success_response(data: Any, meta: Dict[str, Any] = None) -> StandardResponse:
    if meta is None:
        meta = {"source": "system", "timestamp": "now"}
    return StandardResponse(success=True, data=data, meta=meta)

def error_response(code: str, message: str) -> StandardResponse:
    return StandardResponse(
        success=False,
        error={"code": code, "message": message}
    )
