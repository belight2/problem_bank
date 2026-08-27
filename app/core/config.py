from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    app_name: str = "Problem Bank API"

    postgres_host: str = "localhost"
    postgres_port: int = 25431
    postgres_db: str = "problem_bank"
    postgres_user: str = "problem_bank"
    postgres_password: str = "problem_bank_local"

    fuseki_base_url: str = "http://localhost:3030"
    fuseki_dataset: str = "problem-bank"
    fuseki_request_timeout_seconds: float = Field(default=5.0, gt=0)

    graph_sync_enabled: bool = True
    graph_sync_poll_seconds: float = Field(default=2.0, gt=0)
    graph_sync_batch_size: int = Field(default=25, ge=1, le=500)
    graph_sync_max_attempts: int = Field(default=5, ge=1, le=100)
    graph_sync_lock_timeout_seconds: int = Field(default=60, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
