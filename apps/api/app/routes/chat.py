import uuid
from fastapi import APIRouter, HTTPException
from app.schemas.response_schema import ChatRequest, ChatResponse
from app.services.pipeline_service import run_pipeline

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Accepts raw natural language, runs full pipeline:
    Parser → Orchestrator → Context Agent → KB → MCP → Intelligence Layer
    Returns final advice/prediction.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = request.session_id or str(uuid.uuid4())

    try:
        result = await run_pipeline(
            raw_input=request.message,
            session_id=session_id
        )
        return ChatResponse(
            session_id=session_id,
            status="success",
            domain=result.get("domain"),
            location=result.get("location"),
            prediction=result.get("prediction"),
            recommendation=result.get("recommendation"),
            risk_assessment=result.get("risk_assessment"),
            explanation=result.get("explanation"),
            final_answer=result.get("final_answer"),
        )
    except Exception as e:
        return ChatResponse(
            session_id=session_id,
            status="error",
            error=str(e),
            final_answer="Sorry, the system encountered an error. Please try again.",
        )
