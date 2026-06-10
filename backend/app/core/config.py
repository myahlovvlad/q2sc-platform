from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration shared by API, workers and local scripts."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    q2sc_env: str = "development"
    q2sc_api_host: str = "0.0.0.0"
    q2sc_api_port: int = 8000
    q2sc_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite+aiosqlite:///./q2sc_dev.sqlite3"
    sync_database_url: str = "sqlite:///./q2sc_dev.sqlite3"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "q2sc_storage"
    s3_secret_key: str = "q2sc_storage_password"
    s3_bucket: str = "q2sc-spectral-vault"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.q2sc_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
