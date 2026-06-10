"""
Entity Linker — V3
Validates cross-references between attractions, restaurants, and trip stops.
Ensures every place_id in the trip plan exists in the attraction/restaurant registry.
Unlinked entities are flagged as warnings (not hard errors) to allow degraded output.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set


@dataclass
class EntityRegistry:
    """Index of all known places by place_id."""
    places: Dict[str, Dict[str, Any]] = field(default_factory=dict)       # attractions
    restaurants: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # restaurants

    def get(self, place_id: str) -> Optional[Dict[str, Any]]:
        return self.places.get(place_id) or self.restaurants.get(place_id)

    def all_ids(self) -> Set[str]:
        return set(self.places.keys()) | set(self.restaurants.keys())


@dataclass
class EntityLinkValidationResult:
    is_valid: bool
    unlinked_entities: List[str] = field(default_factory=list)
    enriched_stops: List[Dict[str, Any]] = field(default_factory=list)  # stops with merged metadata
    warnings: List[str] = field(default_factory=list)


class EntityLinker:
    """Cross-references place_ids across attractions, restaurants, and trip stops."""

    def build_registry(
        self,
        attractions: List[Dict[str, Any]],
        restaurants: List[Dict[str, Any]],
    ) -> EntityRegistry:
        """Build a flat registry of all known place_ids."""
        registry = EntityRegistry()
        for a in attractions:
            pid = a.get("place_id")
            if pid:
                registry.places[pid] = a
        for r in restaurants:
            pid = r.get("place_id")
            if pid:
                registry.restaurants[pid] = r
        return registry

    def validate_trip_plan(
        self,
        trip_plan: Dict[str, Any],
        registry: EntityRegistry,
    ) -> EntityLinkValidationResult:
        """
        Check every stop in trip_plan has a valid place_id in registry.
        For unlinked stops: add a warning but don't remove them (graceful degradation).
        """
        unlinked = []
        enriched_stops = []
        warnings = []

        for day in trip_plan.get("days", []):
            for stop in day.get("stops", []):
                pid = stop.get("place_id", "")
                entity = registry.get(pid) if pid else None

                if entity:
                    # Merge missing metadata from registry into stop
                    enriched = {**stop}
                    if not enriched.get("lat") and entity.get("latitude"):
                        enriched["lat"] = entity["latitude"]
                    if not enriched.get("lon") and entity.get("longitude"):
                        enriched["lon"] = entity["longitude"]
                    if not enriched.get("is_indoor") and "is_indoor" in entity:
                        enriched["is_indoor"] = entity["is_indoor"]
                    if not enriched.get("vibe_tags") and entity.get("vibe_tags"):
                        enriched["vibe_tags"] = entity["vibe_tags"]
                    enriched_stops.append(enriched)
                else:
                    # Keep stop as-is but flag it
                    enriched_stops.append(stop)
                    if pid:
                        unlinked.append(pid)
                        warnings.append(
                            f"Stop '{stop.get('name', pid)}' (place_id={pid}) not found in registry."
                        )

        return EntityLinkValidationResult(
            is_valid=len(unlinked) == 0,
            unlinked_entities=unlinked,
            enriched_stops=enriched_stops,
            warnings=warnings,
        )

    def enrich_stops_with_forecast(
        self,
        stops: List[Dict[str, Any]],
        daily_forecasts: List[Dict[str, Any]],
        day_idx: int,
    ) -> List[Dict[str, Any]]:
        """
        Inject per-stop forecast data (temp, condition) from daily_forecasts.
        Matches stop.planned_time to the closest hourly snapshot.
        """
        if not daily_forecasts or day_idx >= len(daily_forecasts):
            return stops

        day_forecast = daily_forecasts[day_idx]
        hourly = {h["hour"][:2]: h for h in day_forecast.get("hourly", [])}

        enriched = []
        for stop in stops:
            s = dict(stop)
            time = s.get("planned_time", "08:00")
            hour_key = time[:2]
            h_data = hourly.get(hour_key, {})
            if h_data and not s.get("forecast_temp"):
                s["forecast_temp"] = h_data.get("temp_c")
                s["weather_condition"] = h_data.get("weather_label", "")
                s["rain_prob_pct"] = h_data.get("rain_prob_pct")
            enriched.append(s)

        return enriched
