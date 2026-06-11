"""Build Path B weather requirements from the context-agent payload."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .schemas import WeatherRequirement


class WeatherRequirementReader:
    """Reads FullyProcessedJSON/FullyProcessedPayload into a weather requirement."""

    def read(self, processed_json: Any) -> WeatherRequirement:
        data = processed_json.model_dump() if hasattr(processed_json, "model_dump") else dict(processed_json)
        geo = data.get("geographical_location") or {}
        coords = geo.get("coordinates") or {}
        time_range = data.get("time_range") or {}
        intel = data.get("intelligence_requirements") or {}
        raw_input = data.get("raw_user_input") or ""
        intent = data.get("intent") or "general"
        domain = data.get("domain") or "tourism"

        latitude = float(coords.get("latitude", 16.0544))
        longitude = float(coords.get("longitude", 108.2022))
        location = data.get("location") or geo.get("city") or "Da Nang"
        required_variables = list(intel.get("weather_variables") or [])
        activity_type = self._activity_type(intent, raw_input, data.get("involved_context", []))
        safety_mode = "conservative" if self._is_conservative(domain, activity_type, raw_input, data.get("user_constraints", [])) else "normal"

        seed = "|".join(
            [
                domain,
                intent,
                location,
                str(latitude),
                str(longitude),
                str(time_range.get("start") or ""),
                str(time_range.get("end") or ""),
                datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
            ]
        )
        request_id = "weather_req_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]

        return WeatherRequirement(
            request_id=request_id,
            domain=domain,
            intent=intent,
            activity_type=activity_type,
            location_name=location,
            latitude=latitude,
            longitude=longitude,
            timezone=time_range.get("timezone") or "Asia/Ho_Chi_Minh",
            start_time=time_range.get("start"),
            end_time=time_range.get("end"),
            required_variables=self._required_variables(required_variables, domain, activity_type),
            safety_mode=safety_mode,
            user_constraints=list(data.get("user_constraints") or []),
            raw_user_input=raw_input,
        )

    def _activity_type(self, intent: str, raw_input: str, involved_context: list[str]) -> str | None:
        text = " ".join([intent, raw_input, " ".join(involved_context)]).lower()
        if any(term in text for term in ["beach", "my khe", "island", "swim", "surf", "marine"]):
            return "beach"
        if any(term in text for term in ["mountain", "hiking", "son tra", "ba na"]):
            return "mountain"
        if any(term in text for term in ["construction", "crane", "concrete", "outdoor worker"]):
            return "construction_site"
        if any(term in text for term in ["irrigation", "harvest", "crop", "disease"]):
            return "agriculture_field"
        if any(term in text for term in ["outdoor", "trip", "travel", "tourism", "sightseeing"]):
            return "outdoor_city"
        return None

    def _is_conservative(
        self,
        domain: str,
        activity_type: str | None,
        raw_input: str,
        constraints: list[str],
    ) -> bool:
        text = " ".join([domain, activity_type or "", raw_input, " ".join(constraints)]).lower()
        return any(
            term in text
            for term in [
                "avoid rain",
                "safety",
                "beach",
                "marine",
                "crane",
                "construction",
                "outdoor",
                "storm",
                "danger",
            ]
        )

    def _required_variables(self, variables: list[str], domain: str, activity_type: str | None) -> list[str]:
        normalized = {
            "temperature": "temperature_c",
            "wind_speed": "wind_speed_kmh",
            "wind_gusts": "wind_gust_kmh",
            "humidity": "humidity_percent",
            "storm_warning": "storm_alert",
        }
        result = [normalized.get(v, v) for v in variables]
        base = ["rain_probability", "precipitation_mm", "temperature_c", "humidity_percent", "wind_speed_kmh"]
        for item in base:
            if item not in result:
                result.append(item)
        if domain == "construction" and "wind_gust_kmh" not in result:
            result.append("wind_gust_kmh")
        if activity_type == "beach":
            for item in ["uv_index", "wave_height_m", "tide_height_m", "storm_alert"]:
                if item not in result:
                    result.append(item)
        return result
