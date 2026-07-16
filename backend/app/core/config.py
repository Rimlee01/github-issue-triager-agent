"""
Centralized application configuration.
All settings loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "GitHub Issue Triager Agent"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # --- LLM (Groq) ---
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.2

    # --- GitHub ---
    GITHUB_TOKEN: str = ""
    GITHUB_API_BASE: str = "https://api.github.com"
    GITHUB_WEBHOOK_SECRET: str = "changeme-webhook-secret"

    # --- PostgreSQL ---
    DATABASE_URL: str = "postgresql+asyncpg://triager:triager@db:5432/triager"
    DATABASE_URL_SYNC: str = "postgresql://triager:triager@db:5432/triager"

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL_SECONDS: int = 3600  # 1 hour cache for issue analysis results

    # --- Vector store ---
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    CHROMA_COLLECTION_PREFIX: str = "repo_"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 200

    # --- Ingestion limits ---
    MAX_FILES_TO_INGEST: int = 150
    MAX_FILE_SIZE_BYTES: int = 200_000
    MAX_ISSUES_TO_INGEST: int = 100
    ALLOWED_CODE_EXTENSIONS: tuple = (
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb",
        ".rs", ".c", ".cpp", ".h", ".hpp", ".md", ".yaml", ".yml",
        ".json", ".toml",
    )

    # --- Agent ---
    DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85
    AGENT_TIMEOUT_SECONDS: int = 120

    # --- Auth ---
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: str = "changeme-api-key"  # override in production
    ENABLE_AUTH: bool = False  # set True in production

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- Sentry ---
    SENTRY_DSN: str = ""

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
