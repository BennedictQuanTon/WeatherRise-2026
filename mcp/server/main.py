"""
MCP Server — V3 Tool gateway for all Weatherise external data routes.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict

from mcp.server.routes import (
    location_router,
    place_router,
    restaurant_router,
    time_router,
    domain_router,
    map_router,
    weather_router,
    agriculture_router,
    construction_router,
)

app = FastAPI(
    title="Weatherise MCP Server",
    description="Tool gateway — location, weather, place, restaurant, map, time, domain routes, agriculture routes, construction routes",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(location_router, prefix="/tools/location", tags=["Location"])
app.include_router(place_router, prefix="/tools/place", tags=["Place"])
app.include_router(restaurant_router, prefix="/tools/place", tags=["Restaurant"])
app.include_router(time_router, prefix="/tools/time", tags=["Time"])
app.include_router(domain_router, prefix="/tools/domain", tags=["Domain"])
app.include_router(map_router, prefix="/tools/map", tags=["Map"])
app.include_router(weather_router, prefix="/tools/weather", tags=["Weather"])
app.include_router(agriculture_router, prefix="/tools/agriculture", tags=["Agriculture"])
app.include_router(construction_router, prefix="/tools/construction", tags=["Construction"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-server", "version": "3.0.0"}


@app.post("/tools/{route_name}")
async def tool_dispatcher(route_name: str, body: Dict[str, Any]):
    raise HTTPException(status_code=404, detail=f"Unknown MCP route: {route_name}")
