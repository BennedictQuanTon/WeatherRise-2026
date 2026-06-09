from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    POSTGRES_URL: str = "postgresql+asyncpg://postgres:weatherise@localhost:5432/weatherise"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379"

    # --- NVIDIA NIM (OpenAI-compatible endpoints) ---
    NIM_LLM_BASE_URL: str = "http://localhost:8001/v1"
    NIM_LLM_MODEL: str = "meta/llama-3.1-70b-instruct"
    NIM_EMBED_BASE_URL: str = "http://localhost:8002/v1"
    NIM_EMBED_MODEL: str = "nvidia/nv-embedqa-e5-v5"
    NGC_API_KEY: str = ""

    # --- Milvus Vector Store ---
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_TOURISM_COLLECTION: str = "tourism_collection"
    MILVUS_FISHERY_COLLECTION: str = "fishery_collection"
    MILVUS_CONSTRUCTION_COLLECTION: str = "construction_collection"
    MILVUS_VECTOR_DIM: int = 1024
    MILVUS_SEARCH_TOP_K: int = 5
    MILVUS_TIMEOUT_SECONDS: float = 5.0

    # --- Professional MCP Servers (Tier 2 Fallback) ---
    MCP_TOURISM_URL: str = "http://localhost:9001"
    MCP_FISHERY_URL: str = "http://localhost:9002"
    MCP_CONSTRUCTION_URL: str = "http://localhost:9003"

    # --- NeMo Guardrails ---
    GUARDRAILS_CONFIG_PATH: str = "app/configs/guardrails"

    # --- Routing ---
    ROUTING_CONFIDENCE_THRESHOLD: float = 0.70

    # --- LangSmith (optional tracing) ---
    LANGSMITH_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_PROJECT: str = "weatherise-phase4"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()