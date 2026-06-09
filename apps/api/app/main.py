from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.routes.health import router as health_router
from apps.api.app.routes.chat import router as chat_router
from apps.api.app.routes.websocket import router as ws_router
from apps.api.app.routes.monitor import router as monitor_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up connections, seed KB if needed
    print("🌦️  Weatherise v2 API starting up...")
    yield
    print("🌦️  Weatherise v2 API shutting down...")


app = FastAPI(
    title="Weatherise v2 API",
    description="Domain-aware multi-agent weather intelligence system",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(ws_router, tags=["WebSocket"])
app.include_router(monitor_router, tags=["Monitor"])
