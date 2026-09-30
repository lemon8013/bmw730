"""Application settings.

This module is the **single source of truth for backend configuration**.
Every tunable value is declared here exactly once, and no other backend module
may hard code configuration: infrastructure code reads what it needs from a
:class:`Settings` instance.

Values are supplied through environment variables or a local ``.env`` file
(see ``.env.example``). No password, token, secret or database credential may
be hard coded here.

A value that is ``None`` means "use the library default", which keeps the
configuration surface explicit without overriding behaviour we do not intend to
change.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Final, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_WILDCARD: Final[str] = "*"

_LOG_LEVELS: Final[tuple[str, ...]] = (
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG",
    "NOTSET",
)


class Settings(BaseSettings):
    """Runtime configuration for the single VCTN FastAPI application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "vctn-api"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # PostgreSQL / SQLAlchemy engine
    # ------------------------------------------------------------------
    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: float = 30.0
    # -1 disables connection recycling, which is the SQLAlchemy default.
    DB_POOL_RECYCLE_SECONDS: int = -1
    DB_POOL_PRE_PING: bool = True
    # None means "follow APP_DEBUG".
    DB_ECHO_SQL: bool | None = None

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = ""
    REDIS_ENCODING: str = "utf-8"
    REDIS_DECODE_RESPONSES: bool = True
    # None means "use the redis library default".
    REDIS_MAX_CONNECTIONS: int | None = None
    REDIS_SOCKET_TIMEOUT_SECONDS: float | None = None

    # ------------------------------------------------------------------
    # HTTP / CORS
    # ------------------------------------------------------------------
    # Comma separated list of allowed browser origins, for example:
    # CORS_ORIGINS=http://localhost:5173,http://localhost:5174
    CORS_ORIGINS: str = Field(default="")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"
    CORS_EXPOSE_HEADERS: str = "X-Trace-ID,X-Request-ID"

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------
    TRACE_ID_HEADER: str = "X-Trace-ID"
    REQUEST_ID_HEADER: str = "X-Request-ID"
    TRACE_ID_MAX_LENGTH: int = 128

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    # Empty string means "derive from APP_DEBUG".
    LOG_LEVEL: str = ""
    LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(name)s [trace_id=%(trace_id)s] %(message)s"
    # Empty string means "use the logging module default".
    LOG_DATE_FORMAT: str = ""
    LOG_STREAM: Literal["stdout", "stderr"] = "stdout"

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
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
    def cors_methods(self) -> list[str]:
        """Return the parsed CORS allow-methods list."""
        return [item.strip() for item in self.CORS_ALLOW_METHODS.split(",") if item.strip()]

    @property
    def cors_headers(self) -> list[str]:
        """Return the parsed CORS allow-headers list."""
        return [item.strip() for item in self.CORS_ALLOW_HEADERS.split(",") if item.strip()]

    @property
    def cors_exposed_headers(self) -> list[str]:
        """Return the parsed CORS expose-headers list."""
        return [item.strip() for item in self.CORS_EXPOSE_HEADERS.split(",") if item.strip()]

    @property
    def resolved_log_level(self) -> str:
        """Return the effective log level name."""
        if self.LOG_LEVEL.strip():
            return self.LOG_LEVEL.strip().upper()
        return "DEBUG" if self.APP_DEBUG else "INFO"

    @property
    def resolved_db_echo(self) -> bool:
        """Return whether the SQLAlchemy engine should echo statements."""
        if self.DB_ECHO_SQL is None:
            return self.APP_DEBUG
        return self.DB_ECHO_SQL

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
        if self.API_PREFIX.endswith("/"):
            raise ValueError("API_PREFIX must not end with '/'")
        if not self.TRACE_ID_HEADER.strip():
            raise ValueError("TRACE_ID_HEADER must not be empty")
        if not self.REQUEST_ID_HEADER.strip():
            raise ValueError("REQUEST_ID_HEADER must not be empty")
        if self.TRACE_ID_MAX_LENGTH <= 0:
            raise ValueError("TRACE_ID_MAX_LENGTH must be a positive integer")
        if self.DB_POOL_SIZE <= 0:
            raise ValueError("DB_POOL_SIZE must be a positive integer")
        if self.DB_MAX_OVERFLOW < 0:
            raise ValueError("DB_MAX_OVERFLOW must not be negative")
        if self.REDIS_MAX_CONNECTIONS is not None and self.REDIS_MAX_CONNECTIONS <= 0:
            raise ValueError("REDIS_MAX_CONNECTIONS must be a positive integer")
        if self.resolved_log_level not in _LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {_LOG_LEVELS}")
        # Touching the property triggers the wildcard-origin validation eagerly.
        _ = self.cors_origins


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process wide settings singleton."""
    return Settings()
