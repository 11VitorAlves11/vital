from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Vital"
    environment: Literal["dev", "prod", "test"] = "dev"

    database_url: str = "postgresql+asyncpg://vital:vital@localhost:5432/vital"

    auth_mode: Literal["oidc", "local"] = "oidc"
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None

    llm_model: str = ""
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    storage_path: str = "/storage"
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
