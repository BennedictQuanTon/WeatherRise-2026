from mcp.routes.location.resolve_coordinates import router as location_router
from mcp.routes.place.search_places import router as place_router
from mcp.routes.place.search_restaurants import router as restaurant_router
from mcp.routes.time.resolve_time_range import router as time_router
from mcp.routes.domain.external_risk_data import router as domain_router
from mcp.routes.map.generate_trip_route import router as map_router

__all__ = [
    "location_router",
    "place_router",
    "restaurant_router",
    "time_router",
    "domain_router",
    "map_router",
]
