from fastapi import APIRouter
import redis
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    """Check system health, including Redis connection."""
    redis_status = "ok"
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            socket_connect_timeout=1
        )
        r.ping()
    except Exception as e:
        redis_status = f"down ({str(e)})"
        
    return {
        "status": "ok",
        "redis": redis_status,
        "llm_endpoint": os.getenv("NVIDIA_BASE_URL", "not_configured"),
        "weather_api": "configured" if os.getenv("OPENWEATHERMAP_API_KEY") else "missing"
    }
