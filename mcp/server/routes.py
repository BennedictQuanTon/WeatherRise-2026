from mcp.routes.location.resolve_coordinates import router as location_router
from mcp.routes.weather.forecast import router as weather_router
from mcp.routes.place.search_places import router as place_router
from mcp.routes.time.resolve_time_range import router as time_router
from mcp.routes.domain.external_risk_data import router as domain_router

__all__ = [
    "location_router",
    "weather_router",
    "place_router",
    "time_router",
    "domain_router",
]
