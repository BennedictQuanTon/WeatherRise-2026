from mcp.routes.location.resolve_coordinates import router as location_router
from mcp.routes.place.search_places import router as place_router
from mcp.routes.place.search_restaurants import router as restaurant_router
from mcp.routes.time.resolve_time_range import router as time_router
from mcp.routes.map.generate_trip_route import router as map_router
from mcp.routes.weather.forecast import router as weather_router
from mcp.routes.agriculture.live_telemetry import router as agriculture_router
from mcp.routes.construction.live_telemetry import router as construction_router

__all__ = [
    "location_router",
    "place_router",
    "restaurant_router",
    "time_router",
    "map_router",
    "weather_router",
    "agriculture_router",
    "construction_router",
]
