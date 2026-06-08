from fastapi import APIRouter
import redis.asyncio as redis

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check():
    await redis.redis_client.ping()
    return {"status": "ok", "redis": "connected", "message": "All systems operational"}
