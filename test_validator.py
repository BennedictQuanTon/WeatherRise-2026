from agents.intelligence_layer.weather_path_b.quality_validator import WeatherQualityValidator
from agents.intelligence_layer.weather_path_b.schemas import StandardWeatherRecord, WeatherRequirement
from datetime import datetime

req = WeatherRequirement(
    request_id="test",
    domain="construction",
    intent="general",
    location_name="Da Nang",
    latitude=16.0,
    longitude=108.0,
    timezone="Asia/Ho_Chi_Minh",
    required_variables=["temperature_c", "humidity_percent", "wind_speed_kmh", "precipitation_mm", "wind_gust_kmh"],
    safety_mode="normal",
    user_constraints=[],
    raw_user_input=""
)

# test OpenMeteo which has everything
r1 = StandardWeatherRecord(
    request_id="test", source_code="open_meteo", location_name="Da Nang", latitude=16.0, longitude=108.0,
    forecast_time_utc="2026-06-11T00:00:00Z", forecast_time_local="2026-06-11T00:00:00Z", fetched_at_utc="2026-06-11T00:00:00Z",
    temperature_c=25.0, humidity_percent=80.0, precipitation_mm=0.0, rain_probability=0.1, wind_speed_kmh=10.0, wind_gust_kmh=15.0
)
# test SevenTimer which is missing wind_gust_kmh and precipitation_mm
r2 = StandardWeatherRecord(
    request_id="test", source_code="seven_timer", location_name="Da Nang", latitude=16.0, longitude=108.0,
    forecast_time_utc="2026-06-11T00:00:00Z", forecast_time_local="2026-06-11T00:00:00Z", fetched_at_utc="2026-06-11T00:00:00Z",
    temperature_c=25.0, humidity_percent=80.0, wind_speed_kmh=10.0
)

val = WeatherQualityValidator()
print(val.validate([r1, r2], req))
