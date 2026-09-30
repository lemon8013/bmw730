"""Application settings.

Every value is supplied through environment variables or a local ``.env`` file.
No password, token, secret or database credential may be hard coded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_WILDCARD: Final[str] = "*"


class Settings(BaseSettings):
    """Runtime configuration for the single VCTN FastAPI application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "vctn-api"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    APP_DEBUG: bool = False

    DATABASE_URL: str = ""
    REDIS_URL: str = ""

    API_PREFIX: str = "/api/v1"

    # Comma separated list of allowed browser origins, for example:
    # CORS_ORIGINS=http://localhost:5173,http://localhost:5174
    CORS_ORIGINS: str = Field(default="")

    @property
    def cors_origins(self) -> tuple[str, ...]:
        """Return the parsed CORS allow-list.

        The wildcard origin is rejected: the frozen Spec forbids
        ``allow_origins=["*"]``.
        """
        items = tuple(item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip())
        if _WILDCARD in items:
            raise ValueError("CORS_ORIGINS must not contain the wildcard origin '*'")
        return items

    @property
    def is_database_configured(self) -> bool:
        return bool(self.DATABASE_URL.strip())

    @property
    def is_redis_configured(self) -> bool:
        return bool(self.REDIS_URL.strip())

    def validate_startup(self) -> None:
        """Fail fast on invalid configuration before the app starts serving."""
        if not self.API_PREFIX.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        # Touching the property triggers the wildcard-origin validation eagerly.
        _ = self.cors_origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process wide settings singleton."""
    return Settings()
