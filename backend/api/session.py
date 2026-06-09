from fastapi import APIRouter, HTTPException
from backend.schemas.session_schema import SessionSchema
from backend.services.redis_store import redis_store
from backend.schemas.response_schema import StandardResponse, success_response, error_response

router = APIRouter(prefix="/session", tags=["Session"])

@router.post("/register", response_model=StandardResponse)
async def register_session(session: SessionSchema):
    try:
        redis_store.save_session(session)
        return success_response(data={"session_id": session.session_id})
    except Exception as e:
        return error_response(code="registration_failed", message=str(e))

@router.get("/{session_id}", response_model=StandardResponse)
async def get_session(session_id: str):
    sess = redis_store.get_session(session_id)
    if not sess:
        return error_response(code="session_not_found", message="Session not found")
    return success_response(data=sess.model_dump())
