"""Unit tests for the configuration system."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_defaults() -> None:
    settings = Settings(DATABASE_URL="", REDIS_URL="", CORS_ORIGINS="")
    assert settings.APP_NAME == "vctn-api"
    assert settings.API_PREFIX == "/api/v1"
    assert settings.cors_origins == ()
    assert settings.is_database_configured is False
    assert settings.is_redis_configured is False


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:5173, http://localhost:5174")
    assert settings.cors_origins == ("http://localhost:5173", "http://localhost:5174")


def test_cors_wildcard_is_rejected() -> None:
    settings = Settings(CORS_ORIGINS="*")
    with pytest.raises(ValueError, match="wildcard"):
        _ = settings.cors_origins


def test_api_prefix_must_start_with_slash() -> None:
    settings = Settings(API_PREFIX="api/v1")
    with pytest.raises(ValueError, match="API_PREFIX"):
        settings.validate_startup()


def test_infrastructure_flags_follow_the_urls() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:secret@localhost:5432/vctn",
        REDIS_URL="redis://localhost:6379/0",
    )
    assert settings.is_database_configured is True
    assert settings.is_redis_configured is True


def test_cors_lists_are_parsed_from_configuration() -> None:
    settings = Settings(
        CORS_ALLOW_METHODS="GET, POST",
        CORS_ALLOW_HEADERS="Content-Type, Authorization",
        CORS_EXPOSE_HEADERS="X-Trace-ID,X-Request-ID",
    )
    assert settings.cors_methods == ["GET", "POST"]
    assert settings.cors_headers == ["Content-Type", "Authorization"]
    assert settings.cors_exposed_headers == ["X-Trace-ID", "X-Request-ID"]


def test_log_level_follows_debug_unless_explicitly_set() -> None:
    assert Settings(APP_DEBUG=True).resolved_log_level == "DEBUG"
    assert Settings(APP_DEBUG=False).resolved_log_level == "INFO"
    assert Settings(APP_DEBUG=True, LOG_LEVEL="warning").resolved_log_level == "WARNING"


def test_db_echo_follows_debug_unless_explicitly_set() -> None:
    assert Settings(APP_DEBUG=True).resolved_db_echo is True
    assert Settings(APP_DEBUG=False).resolved_db_echo is False
    assert Settings(APP_DEBUG=True, DB_ECHO_SQL=False).resolved_db_echo is False


def test_pool_settings_are_carried_on_the_settings_object() -> None:
    settings = Settings(
        DB_POOL_SIZE=7,
        DB_MAX_OVERFLOW=3,
        DB_POOL_TIMEOUT_SECONDS=12.5,
        DB_POOL_RECYCLE_SECONDS=600,
        DB_POOL_PRE_PING=False,
        REDIS_MAX_CONNECTIONS=42,
        REDIS_SOCKET_TIMEOUT_SECONDS=2.5,
    )
    assert settings.DB_POOL_SIZE == 7
    assert settings.DB_MAX_OVERFLOW == 3
    assert settings.DB_POOL_TIMEOUT_SECONDS == 12.5
    assert settings.DB_POOL_RECYCLE_SECONDS == 600
    assert settings.DB_POOL_PRE_PING is False
    assert settings.REDIS_MAX_CONNECTIONS == 42
    assert settings.REDIS_SOCKET_TIMEOUT_SECONDS == 2.5


def test_redis_pool_overrides_default_to_library_defaults() -> None:
    settings = Settings()
    assert settings.REDIS_MAX_CONNECTIONS is None
    assert settings.REDIS_SOCKET_TIMEOUT_SECONDS is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"API_PREFIX": "/api/v1/"}, "must not end with"),
        ({"TRACE_ID_HEADER": ""}, "TRACE_ID_HEADER"),
        ({"REQUEST_ID_HEADER": " "}, "REQUEST_ID_HEADER"),
        ({"TRACE_ID_MAX_LENGTH": 0}, "TRACE_ID_MAX_LENGTH"),
        ({"DB_POOL_SIZE": 0}, "DB_POOL_SIZE"),
        ({"DB_MAX_OVERFLOW": -1}, "DB_MAX_OVERFLOW"),
        ({"REDIS_MAX_CONNECTIONS": 0}, "REDIS_MAX_CONNECTIONS"),
        ({"LOG_LEVEL": "LOUD"}, "LOG_LEVEL"),
    ],
)
def test_invalid_configuration_fails_fast(overrides: dict[str, object], message: str) -> None:
    settings = Settings(**overrides)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=message):
        settings.validate_startup()
