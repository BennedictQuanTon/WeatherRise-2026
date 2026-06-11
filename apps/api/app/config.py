from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # NIM
    nim_llm_base_url: str = "http://localhost:8001/v1"
    nim_llm_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nim_embed_base_url: str = "http://localhost:8002/v1"
    nim_embed_model: str = "nvidia/nv-embedqa-e5-v5"

    # Storage
    redis_url: str = "redis://localhost:6379"
    postgres_url: str = "postgresql://weatherise:weatherise@localhost:5432/weatherise"
    qdrant_url: str = "http://localhost:6333"

    # Services
    mcp_server_url: str = "http://localhost:9000"

    # App
    app_env: str = "production"
    log_level: str = "info"
    timezone: str = "Asia/Ho_Chi_Minh"

    # Weather
    openweathermap_api_key: str = ""
    owm_api_key: str = ""
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"
    openweathermap_base_url: str = "https://api.openweathermap.org/data/2.5"
    weatherapi_base_url: str = "https://api.weatherapi.com/v1"
    tomorrow_io_base_url: str = "https://api.tomorrow.io/v4"
    visual_crossing_base_url: str = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services"
    seven_timer_base_url: str = "https://www.7timer.info/bin/api.pl"
    stormglass_base_url: str = "https://api.stormglass.io/v2"
    weather_evidence_dir: str = "/raid/team/weatherise/weather_evidence"
    weather_evidence_fallback_dir: str = "data/weather_evidence"
    nim_weather_arbiter_enabled: bool = True
    nim_weather_arbiter_model: str = ""
    earth2studio_enabled: bool = False
    earth2_output_dir: str = "/raid/team/weatherise/weather_evidence/earth2_processed"
    weatherapi_key: str = ""
    tomorrow_io_api_key: str = ""
    visual_crossing_api_key: str = ""
    weatherbit_api_key: str = ""
    meteosource_api_key: str = ""
    stormglass_api_key: str = ""
    accuweather_api_key: str = ""
    qwen_localizer_enabled: bool = True
    qwen_localizer_base_url: str = "http://localhost:8003/v1"
    qwen_localizer_model: str = "weatherise-parser-qwen35-27b"
    qwen_localizer_timeout_seconds: int = 20
    qwen_localizer_max_tokens: int = 2048

    # Default location
    default_lat: float = 16.0544
    default_lon: float = 108.2022
    default_city: str = "Da Nang"
    default_country: str = "Vietnam"

    # API keys in .env but not needed in Python config
    ngc_api_key: str = ""
    api_url: str = "http://api:8000"
    app_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
