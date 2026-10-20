from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All backend configuration, loaded from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MAX_CONCURRENCY: int = 2
    GEMINI_MIN_INTERVAL_SECONDS: float = 4.0
    GEMINI_TIMEOUT_SECONDS: float = 60.0

    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    EMBEDDING_CACHE_DIR: str = "./.model_cache"

    FRONTEND_ORIGINS: str = "http://localhost:5173"

    MAX_FILE_MB: float = 1.0
    MAX_FILES_PER_UPLOAD: int = 20
    MAX_PAGES: int = 2
    MAX_RESUMES_PER_USER: int = 500
    MAX_TEXT_CHARS: int = 30000
    MIN_TEXT_CHARS: int = 200

    SEARCH_CANDIDATE_POOL: int = 15
    SEARCH_DEFAULT_TOP_K: int = 10
    SEARCH_MAX_TOP_K: int = 25
    SEARCH_RATE_LIMIT_PER_MIN: int = 30

    SIGNED_URL_TTL_SECONDS: int = 3600
    STALE_PROCESSING_MINUTES: int = 10
    WORKER_POLL_SECONDS: float = 3.0

    STORAGE_BUCKET: str = "resumes"

    @property
    def frontend_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_ORIGINS.split(",") if o.strip()]

    @property
    def max_file_bytes(self) -> int:
        return int(self.MAX_FILE_MB * 1024 * 1024)

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
