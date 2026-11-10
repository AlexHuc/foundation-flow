"""Application configuration, sourced from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Either set DATABASE_URL directly, or the individual POSTGRES_* variables
    (matching the names used by infrastructure/.env.example).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "analytics"
    postgres_user: str = "airflow"
    postgres_password: str = ""

    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    @property
    def dsn(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
