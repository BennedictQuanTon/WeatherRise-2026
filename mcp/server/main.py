"""
MCP Server — Tool gateway for all Weatherise external data routes.
Exposes POST /tools/{route_name} endpoints.
Context Agents call this server for missing context.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict

from mcp.server.routes import (
    location_router,
    weather_router,
    place_router,
    time_router,
    domain_router,
)

app = FastAPI(
    title="Weatherise MCP Server",
    description="Tool gateway — location, weather, place, time, domain routes",
    version="2.0.0",
)

# Register all route groups
app.include_router(location_router, prefix="/tools/location", tags=["Location"])
app.include_router(weather_router, prefix="/tools/weather", tags=["Weather"])
app.include_router(place_router, prefix="/tools/place", tags=["Place"])
app.include_router(time_router, prefix="/tools/time", tags=["Time"])
app.include_router(domain_router, prefix="/tools/domain", tags=["Domain"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-server"}


@app.post("/tools/{route_name}")
async def tool_dispatcher(route_name: str, body: Dict[str, Any]):
    """Catch-all dispatcher for unknown routes — returns 404."""
    raise HTTPException(status_code=404, detail=f"Unknown MCP route: {route_name}")
