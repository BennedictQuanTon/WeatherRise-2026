from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from .utils.redis import redis_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup phase: Establish the global Redis connection pool
    app.state.redis = redis_manager.initialize_pool()
    
    # Verify loopback connectivity immediately on boot
    try:
        await app.state.redis.ping()
        print("[STARTUP] Async Redis client handshake successful.")
    except Exception as e:
        print(f"[CRITICAL] Redis handshake aborted: {e}")
        raise e
        
    yield
    
    # 2. Shutdown phase: Safely flush and release socket pools
    await redis_manager.close_pool()

app = FastAPI(title="Weatherise", lifespan=lifespan)

@app.get("/health")
async def health_check():
    try:
        await app.state.redis.ping()
        return {"status": "healthy", "redis": "connected", "message": "All systems operational"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {e}")