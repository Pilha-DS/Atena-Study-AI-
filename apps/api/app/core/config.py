from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://atena:atena@localhost:5432/atena_study"
    cors_origins: str = "http://localhost:3100,http://localhost:3000"
    qdrant_url: str = "http://localhost:6333"
    app_name: str = "Atena Study AI"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
