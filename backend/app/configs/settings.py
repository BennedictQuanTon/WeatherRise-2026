from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:weatherise@localhost:5432/weatherise"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
settings = Settings()