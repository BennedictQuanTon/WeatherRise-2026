from fastapi import APIRouter

from backend.schemas.response_schema import StandardResponse, success_response

router = APIRouter(prefix="/notify", tags=["Notification"])

@router.post("/test", response_model=StandardResponse)
async def test_notify():
    return success_response(data={"message": "Notification system is reachable"})
