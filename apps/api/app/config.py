from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # NIM
    nim_llm_base_url: str = "http://localhost:8001/v1"
    nim_llm_model: str = "nvidia/llama-3.1-nemotron-nano-8b-v1"
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
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

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
