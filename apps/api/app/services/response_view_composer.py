"""
Deterministic response-view composer for demo frontend contracts.

This module converts the existing pipeline result into frontend-ready
weather_prediction and trip_planning view models. LLM text can improve
wording, but dates, coordinates, weather numbers, and risk labels are derived
from structured context and Path B/MCP evidence.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import re
from typing import Any, Optional

from apps.api.app.schemas.response_schema import (
    DailyForecastItem,
    DateRange,
    LocationPoint,
    MapMarker,
    TripMap,
    TripPlanningView,
    TripSummaryCards,
    TripViewDay,
    TripViewDayWeather,
    TripViewStop,
    WeatherAlternative,
    WeatherAssumption,
    WeatherInsight,
    WeatherMap,
    WeatherPredictionView,
    WeatherStatistics,
)


class ResponseViewComposer:
    """Builds validated frontend view payloads from deterministic data."""

    def compose(
        self,
        *,
        processed: Any | None,
        intent_subtype: Optional[str],
        intelligence_output: Any | None,
        trip_plan: Optional[dict[str, Any]],
        coordinates: Optional[dict[str, float]],
        time_range: Optional[dict[str, str]],
        weather_stats: Optional[dict[str, Any]],
        weather_debug: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        response_type = self._response_type(processed, intent_subtype, trip_plan)
        if response_type == "trip_planning":
            trip_view = self._build_trip_view(
                processed=processed,
                intelligence_output=intelligence_output,
                trip_plan=trip_plan,
                coordinates=coordinates,
                time_range=time_range,
                weather_stats=weather_stats,
                weather_debug=weather_debug,
            )
            return {
                "response_type": response_type,
                "weather_view": None,
                "trip_view": trip_view.model_dump() if trip_view else None,
            }
        if response_type == "weather_prediction":
            weather_view = self._build_weather_view(
                processed=processed,
                intelligence_output=intelligence_output,
                coordinates=coordinates,
                time_range=time_range,
                weather_stats=weather_stats,
                weather_debug=weather_debug,
            )
            return {
                "response_type": response_type,
                "weather_view": weather_view.model_dump() if weather_view else None,
                "trip_view": None,
            }
        return {"response_type": "general", "weather_view": None, "trip_view": None}

    def _response_type(
        self,
        processed: Any | None,
        intent_subtype: Optional[str],
        trip_plan: Optional[dict[str, Any]],
    ) -> str:
        domain = self._get(processed, "domain")
        if domain == "unknown":
            return "general"
        if intent_subtype == "multi_day_trip_planning" or trip_plan:
            return "trip_planning"
        if domain in {"tourism", "construction", "agriculture"}:
            return "weather_prediction"
        return "general"

    def _build_weather_view(
        self,
        *,
        processed: Any | None,
        intelligence_output: Any | None,
        coordinates: Optional[dict[str, float]],
        time_range: Optional[dict[str, str]],
        weather_stats: Optional[dict[str, Any]],
        weather_debug: Optional[dict[str, Any]],
    ) -> Optional[WeatherPredictionView]:
        location = self._location(processed, coordinates)
        if not location:
            return None

        lang = self._response_language(intelligence_output)
        date_range = self._date_range(processed, time_range)
        daily = self._daily_forecasts(processed, weather_debug, date_range)
        stats = self._weather_statistics(daily, weather_stats, intelligence_output, weather_debug)
        risk = self._overall_risk(intelligence_output, stats.overall_risk)
        title = (
            f"Thời tiết {location.name} {date_range.label or ''}".strip()
            if lang == "vi"
            else f"{location.name} Weather {date_range.label or ''}".strip()
        )
        assumption = self._assumption(intelligence_output, risk, lang)
        recommendations = self._recommendations(intelligence_output, risk)
        alternatives = self._weather_alternatives(processed, location, risk, lang)
        insights = self._weather_insights(intelligence_output, stats, risk, lang)

        avg_marker_temp = stats.avg_temperature_c
        marker = MapMarker(
            id="weather-location",
            label=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            title=location.name,
            description=f"Avg Temp: {avg_marker_temp}C" if avg_marker_temp is not None else None,
            temperature_c=avg_marker_temp,
            weather_condition=stats.most_common_condition,
            rain_probability=self._max_rain_probability(daily),
        )

        return WeatherPredictionView(
            title=title,
            location=location,
            date_range=date_range,
            assumption=assumption,
            statistics=stats,
            daily_forecast=daily,
            recommendations=recommendations,
            alternatives=alternatives,
            map=WeatherMap(center=location, markers=[marker]),
            insights=insights,
        )

    def _build_trip_view(
        self,
        *,
        processed: Any | None,
        intelligence_output: Any | None,
        trip_plan: Optional[dict[str, Any]],
        coordinates: Optional[dict[str, float]],
        time_range: Optional[dict[str, str]],
        weather_stats: Optional[dict[str, Any]],
        weather_debug: Optional[dict[str, Any]],
    ) -> Optional[TripPlanningView]:
        if not trip_plan:
            return None

        lang = self._response_language(intelligence_output)
        location_name = trip_plan.get("location") or self._get(processed, "location") or "Destination"
        date_range = self._date_range(processed, time_range)
        daily = self._daily_forecasts(processed, weather_debug, date_range)
        days = []
        markers: list[MapMarker] = []

        for day_index, day in enumerate(trip_plan.get("days", [])):
            day_num = int(day.get("day") or day_index + 1)
            day_forecast = daily[day_index] if day_index < len(daily) else None
            date = day.get("date") or (day_forecast.date if day_forecast else self._date_for_index(date_range, day_index))
            weather = TripViewDayWeather(
                high_c=self._number(day_forecast.max_temp_c if day_forecast else None),
                low_c=self._number(day_forecast.min_temp_c if day_forecast else None),
                rain_probability=day_forecast.rain_probability if day_forecast else self._rain_fraction(day.get("rain_prob")),
                condition=day.get("weather_condition") or (day_forecast.condition if day_forecast else None),
            )
            stops = []
            for stop_index, stop in enumerate(day.get("stops", [])):
                stop_view = self._trip_stop(stop, day_forecast, day_num, stop_index, lang)
                stops.append(stop_view)
                markers.append(MapMarker(
                    id=f"day-{day_num}-stop-{stop_view.order}",
                    label=stop_view.name,
                    latitude=stop_view.latitude,
                    longitude=stop_view.longitude,
                    title=stop_view.name,
                    description=stop_view.description,
                    order=stop_view.order,
                    category=stop_view.category,
                    temperature_c=stop_view.forecast_temp_c,
                    weather_condition=stop_view.weather_condition,
                    rain_probability=stop_view.rain_probability,
                    is_indoor=stop_view.is_indoor,
                ))

            title_date = self._display_date(date)
            days.append(TripViewDay(
                day=day_num,
                date=date,
                title=(
                    f"Ngày {day_num}{f' - {title_date}' if title_date else ''}"
                    if lang == "vi"
                    else f"Day {day_num}{f' - {title_date}' if title_date else ''}"
                ),
                summary=self._day_summary(day, day_forecast, intelligence_output, lang),
                weather=weather,
                stops=stops,
            ))

        summary_cards = self._trip_summary_cards(daily, weather_stats, weather_debug)
        ai_summary = self._ai_summary(intelligence_output, summary_cards, location_name, lang)

        return TripPlanningView(
            title=f"Kế hoạch cho {location_name}" if lang == "vi" else f"Plan for {location_name}",
            date_range=date_range,
            summary_cards=summary_cards,
            ai_summary=ai_summary,
            days=days,
            map=TripMap(markers=markers),
        )

    def _trip_stop(
        self,
        stop: dict[str, Any],
        day_forecast: Optional[DailyForecastItem],
        day_num: int,
        stop_index: int,
        lang: str,
    ) -> TripViewStop:
        rain_probability = self._rain_fraction(stop.get("rain_prob_pct"))
        if rain_probability is None and day_forecast:
            rain_probability = day_forecast.rain_probability
        is_indoor = bool(stop.get("is_indoor", False))
        suitability = self._weather_suitability(rain_probability, is_indoor)
        time_block = stop.get("time_block") or "activity"
        description = self._stop_description(stop, lang)

        return TripViewStop(
            order=int(stop.get("order") or stop_index + 1),
            time=stop.get("planned_time") or "08:00",
            time_block=time_block,
            category=stop.get("category") or "attraction",
            name=stop.get("name") or f"Stop {stop_index + 1}",
            description=description,
            latitude=float(stop.get("lat") or stop.get("latitude") or 16.0544),
            longitude=float(stop.get("lon") or stop.get("longitude") or 108.2022),
            forecast_temp_c=self._number(stop.get("forecast_temp") or (self._mid_temp(day_forecast) if day_forecast else None)),
            rain_probability=rain_probability,
            weather_condition=stop.get("weather_condition") or (day_forecast.condition if day_forecast else None),
            is_indoor=is_indoor,
            weather_suitability=suitability,
        )

    def _daily_forecasts(
        self,
        processed: Any | None,
        weather_debug: Optional[dict[str, Any]],
        date_range: DateRange,
    ) -> list[DailyForecastItem]:
        mcp_daily = self._extract_mcp_daily(processed)
        if mcp_daily:
            return [self._daily_from_mcp(item) for item in mcp_daily]

        selected = (weather_debug or {}).get("selected_weather") or {}
        if selected:
            return self._daily_from_selected_weather(selected, date_range)

        return []

    def _daily_from_mcp(self, item: dict[str, Any]) -> DailyForecastItem:
        condition = item.get("dominant_weather") or item.get("weather_label") or "Unknown"
        rain_probability = self._rain_fraction(item.get("max_rain_prob_pct"))
        return DailyForecastItem(
            date=item.get("date") or "",
            day_label=(item.get("day_label") or self._display_date(item.get("date")) or item.get("date") or ""),
            condition=condition,
            condition_icon=self._condition_icon(condition),
            max_temp_c=self._number(item.get("max_temp_c")),
            min_temp_c=self._number(item.get("min_temp_c")),
            wind_kmh=self._number(item.get("max_wind_kmh")),
            rain_probability=rain_probability,
            rain_mm=self._number(item.get("precipitation_mm") or item.get("rain_mm")),
            risk=item.get("overall_risk") or self._risk_from_fraction(rain_probability),
        )

    def _daily_from_selected_weather(
        self,
        selected: dict[str, Any],
        date_range: DateRange,
    ) -> list[DailyForecastItem]:
        dates = self._date_span(date_range.start, date_range.end, max_days=7)
        if not dates:
            dates = [date_range.start or datetime.utcnow().strftime("%Y-%m-%d")]
        temp = self._number(selected.get("temperature_c"))
        rain_probability = self._rain_fraction(selected.get("rain_probability"))
        condition = selected.get("weather_description") or "Weather snapshot"
        return [
            DailyForecastItem(
                date=date,
                day_label=self._display_date(date) or date,
                condition=condition,
                condition_icon=self._condition_icon(condition),
                max_temp_c=temp,
                min_temp_c=temp,
                wind_kmh=self._number(selected.get("wind_speed_kmh")),
                rain_probability=rain_probability,
                rain_mm=self._number(selected.get("precipitation_mm")),
                risk=self._risk_from_fraction(rain_probability),
            )
            for date in dates
        ]

    def _weather_statistics(
        self,
        daily: list[DailyForecastItem],
        weather_stats: Optional[dict[str, Any]],
        intelligence_output: Any | None,
        weather_debug: Optional[dict[str, Any]],
    ) -> WeatherStatistics:
        highs = [d.max_temp_c for d in daily if d.max_temp_c is not None]
        lows = [d.min_temp_c for d in daily if d.min_temp_c is not None]
        winds = [d.wind_kmh for d in daily if d.wind_kmh is not None]
        rain_mm = [d.rain_mm for d in daily if d.rain_mm is not None]
        conditions = [d.condition for d in daily if d.condition]

        stats = weather_stats or {}
        selected = (weather_debug or {}).get("selected_weather") or {}
        risk = self._risk_dict(intelligence_output)
        avg_temp_values = []
        if highs:
            avg_temp_values.extend(highs)
        if lows:
            avg_temp_values.extend(lows)
        if not avg_temp_values and selected.get("temperature_c") is not None:
            avg_temp_values.append(selected.get("temperature_c"))

        return WeatherStatistics(
            avg_temperature_c=self._avg(avg_temp_values),
            min_temperature_c=self._number(min(lows) if lows else stats.get("min_temp") or selected.get("temperature_c")),
            max_temperature_c=self._number(max(highs) if highs else stats.get("max_temp") or selected.get("temperature_c")),
            avg_wind_kmh=self._avg(winds) or self._number(stats.get("max_wind_speed") or selected.get("wind_speed_kmh")),
            total_rainfall_mm=self._number(sum(rain_mm)) if rain_mm else self._number(selected.get("precipitation_mm")),
            rain_risk=risk.get("rain_risk"),
            wind_risk=risk.get("wind_risk"),
            heat_risk=risk.get("heat_risk"),
            overall_risk=self._overall_risk(intelligence_output, None),
            most_common_condition=Counter(conditions).most_common(1)[0][0] if conditions else selected.get("weather_description"),
        )

    def _trip_summary_cards(
        self,
        daily: list[DailyForecastItem],
        weather_stats: Optional[dict[str, Any]],
        weather_debug: Optional[dict[str, Any]],
    ) -> TripSummaryCards:
        highs = [d.max_temp_c for d in daily if d.max_temp_c is not None]
        lows = [d.min_temp_c for d in daily if d.min_temp_c is not None]
        winds = [d.wind_kmh for d in daily if d.wind_kmh is not None]
        rain = [d.rain_probability for d in daily if d.rain_probability is not None]
        selected = (weather_debug or {}).get("selected_weather") or {}
        stats = weather_stats or {}
        humidity = selected.get("humidity_percent")

        return TripSummaryCards(
            avg_high_c=self._avg(highs) or self._number(stats.get("max_temp") or selected.get("temperature_c")),
            avg_low_c=self._avg(lows) or self._number(selected.get("temperature_c")),
            avg_wind_kmh=self._avg(winds) or self._number(stats.get("max_wind_speed") or selected.get("wind_speed_kmh")),
            humidity_percent=self._number(humidity),
            rain_risk=self._risk_from_fraction(max(rain) if rain else self._rain_fraction(stats.get("max_rain_prob"))),
        )

    def _location(
        self,
        processed: Any | None,
        coordinates: Optional[dict[str, float]],
    ) -> Optional[LocationPoint]:
        coords = coordinates or self._get(processed, "geographical_location", "coordinates") or {}
        lat = coords.get("latitude") if isinstance(coords, dict) else None
        lon = coords.get("longitude") if isinstance(coords, dict) else None
        if lat is None or lon is None:
            return None
        name = self._get(processed, "location") or self._get(processed, "geographical_location", "city") or "Selected location"
        return LocationPoint(name=str(name), latitude=float(lat), longitude=float(lon))

    def _date_range(self, processed: Any | None, time_range: Optional[dict[str, str]]) -> DateRange:
        tr = time_range or {}
        start = tr.get("start") or self._get(processed, "time_range", "start")
        end = tr.get("end") or self._get(processed, "time_range", "end")
        label = tr.get("raw_text") or self._get(processed, "time_range", "raw_text")
        return DateRange(start=start, end=end, label=self._label_time_range(label, start, end))

    def _extract_mcp_daily(self, processed: Any | None) -> list[dict[str, Any]]:
        mcp = self._get(processed, "mcp_context") or {}
        weather_forecast = self._get(mcp, "weather_forecast") or {}
        if not isinstance(weather_forecast, dict):
            return []
        if isinstance(weather_forecast.get("output"), dict):
            return weather_forecast["output"].get("daily_forecasts") or []
        return weather_forecast.get("daily_forecasts") or []

    def _weather_alternatives(
        self,
        processed: Any | None,
        location: LocationPoint,
        risk: str,
        lang: str,
    ) -> list[WeatherAlternative]:
        places = self._extract_places(processed)
        if places:
            indoor_first = risk in {"medium", "high"}
            ranked = sorted(
                places,
                key=lambda p: (not bool(p.get("is_indoor", False)) if indoor_first else bool(p.get("is_indoor", False)))
            )
            alternatives = []
            for place in ranked[:4]:
                alternatives.append(WeatherAlternative(
                    name=place.get("name_vi") or place.get("name") or "Nearby option",
                    description=self._place_description(place, indoor_first, lang),
                    distance_label=self._distance_label(location, place),
                    latitude=self._number(place.get("latitude")),
                    longitude=self._number(place.get("longitude")),
                ))
            return alternatives
        if risk in {"medium", "high"}:
            return [
                WeatherAlternative(
                    name=(
                        f"Phương án trong nhà quanh {location.name}"
                        if lang == "vi"
                        else f"Indoor options around {location.name}"
                    ),
                    description=(
                        "Ưu tiên nhà hàng, bảo tàng, quán cà phê hoặc chợ có mái che nếu mưa hoặc gió tăng."
                        if lang == "vi"
                        else "Use covered dining, museums, cafes, or markets if rain or wind risk increases."
                    ),
                )
            ]
        return []

    def _extract_places(self, processed: Any | None) -> list[dict[str, Any]]:
        mcp = self._get(processed, "mcp_context") or {}
        places = self._get(mcp, "places") or []
        if isinstance(places, dict):
            places = places.get("output", {}).get("attractions", [])
        return places if isinstance(places, list) else []

    def _assumption(self, intelligence_output: Any | None, risk: str, lang: str) -> WeatherAssumption:
        should_go = risk != "high"
        if risk == "high":
            label = "KHÔNG" if lang == "vi" else "NO"
            reason = (
                "Rủi ro thời tiết cao; nên dùng phương án trong nhà hoặc dời hoạt động ngoài trời."
                if lang == "vi"
                else "Weather risk is high; use indoor backups or delay exposed activities."
            )
        elif risk == "medium":
            label = "CÂN NHẮC" if lang == "vi" else "CAUTION"
            reason = (
                "Có thể đi, nhưng nên giữ lịch linh hoạt và chuẩn bị phương án trong nhà."
                if lang == "vi"
                else "Conditions are usable, but keep flexible timing and indoor backups."
            )
        else:
            label = "CÓ" if lang == "vi" else "YES"
            reason = (
                "Rủi ro thời tiết thấp cho kế hoạch đã hỏi."
                if lang == "vi"
                else "Weather risk is low for the requested plan."
            )
        fragments = self._llm_fragments(intelligence_output)
        summary = fragments.get("assumption_summary") if isinstance(fragments.get("assumption_summary"), str) else None
        summary = summary or self._get(intelligence_output, "explanation") or (
            "Dự báo dựa trên bằng chứng thời tiết đa nguồn đã được kiểm chứng."
            if lang == "vi"
            else "Forecast is based on deterministic multi-source weather evidence."
        )
        return WeatherAssumption(summary=summary, should_go=should_go, decision_label=label, reason=reason)

    def _recommendations(self, intelligence_output: Any | None, risk: str) -> list[str]:
        fragments = self._llm_fragments(intelligence_output)
        bullets = fragments.get("recommendation_bullets")
        if isinstance(bullets, list) and bullets:
            return [str(item) for item in bullets[:6]]
        text = self._get(intelligence_output, "recommendation") or self._get(intelligence_output, "final_answer") or ""
        recs = self._split_sentences(text)
        if recs:
            return recs[:6]
        if risk == "high":
            return ["Prioritize indoor or covered activities and avoid exposed outdoor plans."]
        if risk == "medium":
            return ["Plan outdoor activities earlier in the day and keep weather-flexible backups."]
        return ["Conditions look suitable for the requested plan; continue checking updates before departure."]

    def _weather_insights(
        self,
        intelligence_output: Any | None,
        stats: WeatherStatistics,
        risk: str,
        lang: str,
    ) -> list[WeatherInsight]:
        fragments = self._llm_fragments(intelligence_output)
        llm_insights = fragments.get("insight_bullets")
        if isinstance(llm_insights, list) and llm_insights:
            insights = []
            for item in llm_insights[:4]:
                if isinstance(item, dict):
                    insights.append(WeatherInsight(
                        title=str(item.get("title") or "Weather note"),
                        body=str(item.get("body") or ""),
                        type=item.get("type") if item.get("type") in {"rain", "wind", "heat", "travel"} else "general",
                    ))
            if insights:
                return insights

        insights = [
            WeatherInsight(
                title="Rủi ro tổng thể" if lang == "vi" else "Overall travel risk",
                body=f"Rủi ro thời tiết tổng thể là {risk}." if lang == "vi" else f"Overall weather risk is {risk}.",
                type="travel",
            )
        ]
        if stats.rain_risk:
            insights.append(WeatherInsight(
                title="Kế hoạch theo mưa" if lang == "vi" else "Rain planning",
                body=(
                    f"Rủi ro mưa là {stats.rain_risk}; nên giữ lịch linh hoạt nếu xuất hiện mưa rào."
                    if lang == "vi"
                    else f"Rain risk is {stats.rain_risk}; keep timing flexible if showers develop."
                ),
                type="rain",
            ))
        if stats.avg_wind_kmh is not None:
            insights.append(WeatherInsight(
                title="Mức gió" if lang == "vi" else "Wind comfort",
                body=(
                    f"Tốc độ gió trung bình khoảng {stats.avg_wind_kmh} km/h."
                    if lang == "vi"
                    else f"Average wind is about {stats.avg_wind_kmh} km/h."
                ),
                type="wind",
            ))
        if stats.max_temperature_c is not None:
            insights.append(WeatherInsight(
                title="Nắng nóng" if lang == "vi" else "Heat exposure",
                body=(
                    f"Nhiệt độ cao nhất khoảng {stats.max_temperature_c}C."
                    if lang == "vi"
                    else f"Peak temperature is around {stats.max_temperature_c}C."
                ),
                type="heat",
            ))
        return insights[:4]

    def _day_summary(
        self,
        day: dict[str, Any],
        day_forecast: Optional[DailyForecastItem],
        intelligence_output: Any | None,
        lang: str,
    ) -> str:
        fragments = self._llm_fragments(intelligence_output)
        day_summaries = fragments.get("trip_day_summaries")
        day_num = day.get("day")
        if isinstance(day_summaries, list):
            for item in day_summaries:
                if isinstance(item, dict) and item.get("day") == day_num and item.get("summary"):
                    return str(item["summary"])
        theme = day.get("theme") or "Balanced day"
        if day_forecast and day_forecast.rain_probability is not None and day_forecast.rain_probability >= 0.6:
            return (
                f"{theme}; ưu tiên điểm trong nhà hoặc có mái che vì rủi ro mưa cao."
                if lang == "vi"
                else f"{theme}; prioritize indoor or covered stops because rain risk is high."
            )
        return (
            f"{theme}; cân bằng bữa ăn, điểm tham quan và thời gian theo thời tiết."
            if lang == "vi"
            else f"{theme}; balance meals, attractions, and weather-aware timing."
        )

    def _ai_summary(
        self,
        intelligence_output: Any | None,
        summary_cards: TripSummaryCards,
        location_name: str,
        lang: str,
    ) -> str:
        final_answer = self._get(intelligence_output, "final_answer")
        if final_answer:
            return str(final_answer)
        rain = summary_cards.rain_risk or "unknown"
        if lang == "vi":
            return f"{location_name} có rủi ro mưa mức {rain} cho kế hoạch này. Hãy dùng lịch từng ngày và bản đồ để canh thời điểm cho các điểm ngoài trời."
        return f"{location_name} has {rain} rain risk for this plan. Use the daily schedule and map markers to time outdoor stops around the weather."

    def _stop_description(self, stop: dict[str, Any], lang: str) -> str:
        tags = stop.get("vibe_tags") or []
        if isinstance(tags, list) and tags:
            return ", ".join(str(tag).replace("_", " ") for tag in tags[:3])
        category = stop.get("category") or "place"
        return f"Điểm dừng {category}" if lang == "vi" else f"{category.title()} stop"

    def _place_description(self, place: dict[str, Any], indoor_first: bool, lang: str) -> str:
        is_indoor = bool(place.get("is_indoor", False))
        tags = place.get("vibe_tags") or []
        tag_text = ", ".join(str(tag).replace("_", " ") for tag in tags[:2]) if isinstance(tags, list) and tags else ""
        if indoor_first and is_indoor:
            if lang == "vi":
                return f"Phương án trong nhà{f' cho {tag_text}' if tag_text else ''}."
            return f"Indoor backup{f' for {tag_text}' if tag_text else ''}."
        if tag_text:
            return tag_text
        if lang == "vi":
            return "Phương án trong nhà." if is_indoor else "Phương án ngoài trời khi thời tiết quang hơn."
        return "Indoor backup." if is_indoor else "Outdoor option for clearer weather."

    def _distance_label(self, location: LocationPoint, place: dict[str, Any]) -> Optional[str]:
        lat = place.get("latitude")
        lon = place.get("longitude")
        if lat is None or lon is None:
            return None
        km = self._haversine_km(location.latitude, location.longitude, float(lat), float(lon))
        return f"{round(km, 1)} km"

    def _weather_suitability(self, rain_probability: Optional[float], is_indoor: bool) -> str:
        if rain_probability is None:
            return "medium"
        if is_indoor:
            return "low" if rain_probability < 0.8 else "medium"
        if rain_probability >= 0.6:
            return "high"
        if rain_probability >= 0.35:
            return "medium"
        return "low"

    def _risk_dict(self, intelligence_output: Any | None) -> dict[str, str]:
        risk = self._get(intelligence_output, "risk_assessment") or {}
        if not isinstance(risk, dict):
            return {}
        return {key: self._risk_value(value) for key, value in risk.items()}

    def _overall_risk(self, intelligence_output: Any | None, fallback: Optional[str]) -> str:
        risk = self._risk_dict(intelligence_output)
        direct = risk.get("overall_risk") or risk.get("trip_disruption_risk") or risk.get("construction_safety_risk") or risk.get("disease_risk")
        if direct:
            return direct
        values = [v for v in risk.values() if v in {"low", "medium", "high"}]
        if "high" in values:
            return "high"
        if values.count("medium") >= 2:
            return "high"
        if "medium" in values:
            return "medium"
        return fallback or "low"

    def _llm_fragments(self, intelligence_output: Any | None) -> dict[str, Any]:
        metadata = self._get(intelligence_output, "metadata") or {}
        if isinstance(metadata, dict) and isinstance(metadata.get("llm_text_fragments"), dict):
            return metadata["llm_text_fragments"]
        return {}

    def _response_language(self, intelligence_output: Any | None) -> str:
        metadata = self._get(intelligence_output, "metadata") or {}
        if isinstance(metadata, dict) and metadata.get("response_language") == "vi":
            return "vi"
        return "en"

    def _get(self, obj: Any, *keys: str) -> Any:
        current = obj
        for key in keys:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            elif hasattr(current, "model_dump"):
                current = current.model_dump().get(key)
            else:
                return None
        return current

    def _number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return round(float(value), 1)
        except (TypeError, ValueError):
            return None

    def _avg(self, values: list[Any]) -> Optional[float]:
        nums = [float(v) for v in values if isinstance(v, (int, float))]
        if not nums:
            return None
        return round(sum(nums) / len(nums), 1)

    def _rain_fraction(self, value: Any) -> Optional[float]:
        num = self._number(value)
        if num is None:
            return None
        if num > 1:
            return round(num / 100, 3)
        return round(num, 3)

    def _risk_from_fraction(self, value: Optional[float]) -> str:
        if value is None:
            return "medium"
        if value >= 0.6:
            return "high"
        if value >= 0.35:
            return "medium"
        return "low"

    def _risk_value(self, value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        text = str(value or "").lower()
        if "high" in text:
            return "high"
        if "medium" in text or "moderate" in text:
            return "medium"
        if "low" in text:
            return "low"
        return text or "unknown"

    def _split_sentences(self, text: str) -> list[str]:
        if not text:
            return []
        raw = re.split(r"(?:\n+|(?<=[.!?])\s+)", text)
        return [item.strip(" -\t") for item in raw if item.strip(" -\t")]

    def _condition_icon(self, condition: str) -> str:
        text = (condition or "").lower()
        if "thunder" in text or "storm" in text:
            return "storm"
        if "rain" in text or "shower" in text or "drizzle" in text:
            return "rain"
        if "cloud" in text or "overcast" in text:
            return "partly_cloudy" if "part" in text or "mainly" in text else "cloudy"
        if "fog" in text:
            return "fog"
        return "sunny"

    def _label_time_range(self, raw: Optional[str], start: Optional[str], end: Optional[str]) -> Optional[str]:
        if raw:
            return str(raw).strip().capitalize()
        if start and end and start != end:
            return f"{start} to {end}"
        return start

    def _display_date(self, date_value: Optional[str]) -> Optional[str]:
        if not date_value:
            return None
        try:
            return datetime.strptime(date_value[:10], "%Y-%m-%d").strftime("%a, %b %d")
        except ValueError:
            return date_value

    def _date_for_index(self, date_range: DateRange, index: int) -> Optional[str]:
        if not date_range.start:
            return None
        try:
            start = datetime.strptime(date_range.start[:10], "%Y-%m-%d")
            return (start + timedelta(days=index)).strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _date_span(self, start: Optional[str], end: Optional[str], max_days: int) -> list[str]:
        if not start:
            return []
        try:
            current = datetime.strptime(start[:10], "%Y-%m-%d")
            last = datetime.strptime((end or start)[:10], "%Y-%m-%d")
        except ValueError:
            return [start]
        dates = []
        while current <= last and len(dates) < max_days:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        return dates

    def _mid_temp(self, forecast: DailyForecastItem) -> Optional[float]:
        temps = [t for t in [forecast.max_temp_c, forecast.min_temp_c] if t is not None]
        return self._avg(temps)

    def _max_rain_probability(self, daily: list[DailyForecastItem]) -> Optional[float]:
        values = [d.rain_probability for d in daily if d.rain_probability is not None]
        return max(values) if values else None

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import asin, cos, radians, sin, sqrt

        radius_km = 6371.0
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)
        a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
        return 2 * radius_km * asin(sqrt(a))
