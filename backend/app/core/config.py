import secrets
from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
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
    oidc_scopes: str = "openid email profile"
    # Set it when the API sits behind a proxy that rewrites scheme or host, so the
    # redirect URI matches the one registered with the provider exactly.
    oidc_redirect_uri: str | None = None

    # Signs the session cookie. Rotating it logs everyone out, which is the point.
    secret_key: str = ""
    session_cookie_name: str = "vital_session"
    session_max_age: int = 60 * 60 * 24 * 14

    # Where the browser lands after an OIDC round-trip.
    frontend_url: str = "http://localhost:5173"

    llm_model: str = ""
    llm_api_key: str | None = None
    llm_base_url: str | None = None

    storage_path: str = "/storage"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def cookies_secure(self) -> bool:
        """Session cookies are HTTPS-only everywhere except local development."""
        return self.environment == "prod"

    @property
    def oidc_metadata_url(self) -> str | None:
        if not self.oidc_issuer:
            return None
        return f"{self.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"

    @model_validator(mode="after")
    def _check_secrets(self) -> Self:
        if not self.secret_key:
            if self.environment == "prod":
                raise ValueError("SECRET_KEY is required when ENVIRONMENT=prod")
            # Dev/test convenience: sessions simply do not survive a restart.
            self.secret_key = secrets.token_urlsafe(32)
        if self.auth_mode == "oidc" and self.environment == "prod":
            missing = [
                name
                for name, value in (
                    ("OIDC_ISSUER", self.oidc_issuer),
                    ("OIDC_CLIENT_ID", self.oidc_client_id),
                    ("OIDC_CLIENT_SECRET", self.oidc_client_secret),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"AUTH_MODE=oidc requires {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
