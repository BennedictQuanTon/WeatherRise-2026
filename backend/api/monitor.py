from fastapi import APIRouter
from backend.agents.weather_watcher_agent import watcher_agent
from backend.schemas.response_schema import StandardResponse, success_response, error_response

router = APIRouter(prefix="/watcher", tags=["Monitoring"])

@router.post("/check-now", response_model=StandardResponse)
async def check_now():
    try:
        alerts = watcher_agent.check_all_sessions()
        return success_response(data={"alerts_generated": len(alerts), "alerts": alerts})
    except Exception as e:
        return error_response(code="check_failed", message=str(e))

@router.post("/simulate-conflict", response_model=StandardResponse)
async def simulate_conflict(session_id: str):
    try:
        alert = watcher_agent.simulate_conflict(session_id)
        if "error" in alert:
            return error_response(code="conflict_simulation_failed", message=alert["error"])
        return success_response(data={"alert": alert})
    except Exception as e:
        return error_response(code="simulation_error", message=str(e))
