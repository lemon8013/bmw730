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


def test_database_url_is_assembled_from_fields() -> None:
    settings = Settings(
        DB_HOST="10.0.0.5",
        DB_PORT=5433,
        DB_NAME="vctn",
        DB_USER="vctn_app",
        DB_PASSWORD="p@ss:word/1",
    )
    assert settings.database_url == (
        "postgresql+asyncpg://vctn_app:p%40ss%3Aword%2F1@10.0.0.5:5433/vctn"
    )
    assert settings.is_database_configured is True


def test_redis_url_is_assembled_from_fields() -> None:
    assert Settings(REDIS_HOST="10.0.0.6").redis_url == "redis://10.0.0.6:6379/0"
    assert (
        Settings(
            REDIS_HOST="10.0.0.6", REDIS_PORT=6380, REDIS_DB=2, REDIS_PASSWORD="s3cr3t"
        ).redis_url
        == "redis://:s3cr3t@10.0.0.6:6380/2"
    )
    assert (
        Settings(REDIS_HOST="10.0.0.6", REDIS_USERNAME="app", REDIS_PASSWORD="s3cr3t").redis_url
        == "redis://app:s3cr3t@10.0.0.6:6379/0"
    )


def test_ipv6_hosts_are_bracketed() -> None:
    assert Settings(DB_HOST="::1", DB_NAME="vctn", DB_USER="u").database_url == (
        "postgresql+asyncpg://u:@[::1]:5432/vctn"
    )
    assert Settings(REDIS_HOST="::1").redis_url == "redis://[::1]:6379/0"


def test_explicit_url_overrides_the_individual_fields() -> None:
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://override:override@override-host:5432/override-db",
        DB_HOST="ignored",
        DB_NAME="ignored",
        DB_USER="ignored",
        REDIS_URL="redis://override-host:6379/9",
        REDIS_HOST="ignored",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://override:override@override-host")
    assert settings.redis_url == "redis://override-host:6379/9"


def test_connection_is_unconfigured_when_fields_are_incomplete() -> None:
    assert Settings(DB_USER="u", DB_NAME="vctn").is_database_configured is False
    assert Settings(DB_HOST="h", DB_NAME="vctn").is_database_configured is False
    assert Settings().is_redis_configured is False


def test_partial_database_configuration_is_reported_not_raised() -> None:
    settings = Settings(DB_HOST="10.0.0.5", DB_NAME="bmw730", DB_USER="")
    assert settings.is_database_configured is False
    assert settings.missing_database_fields == ("DB_USER",)
    # A partially filled .env must not break startup.
    settings.validate_startup()


def test_missing_database_fields_is_empty_when_complete_or_unset() -> None:
    assert Settings(DB_HOST="h", DB_NAME="d", DB_USER="u").missing_database_fields == ()
    assert Settings().missing_database_fields == ()
    assert Settings(DATABASE_URL="postgresql+asyncpg://u:p@h:5432/d").missing_database_fields == ()


def test_blank_values_fall_back_to_defaults() -> None:
    """A blank line in .env must behave like an absent key."""
    settings = Settings(
        DB_ECHO_SQL="",
        REDIS_MAX_CONNECTIONS="",
        REDIS_SOCKET_TIMEOUT_SECONDS="",
        DB_PORT="",
        LOG_LEVEL="",
        CORS_ORIGINS="",
    )
    assert settings.DB_ECHO_SQL is None
    assert settings.REDIS_MAX_CONNECTIONS is None
    assert settings.REDIS_SOCKET_TIMEOUT_SECONDS is None
    assert settings.DB_PORT == 5432
    assert settings.resolved_log_level == "INFO"
    assert settings.cors_origins == ()


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
        ({"API_PREFIX": "api/v1"}, "must start with"),
        ({"TRACE_ID_MAX_LENGTH": 0}, "TRACE_ID_MAX_LENGTH"),
        ({"DB_PORT": 70000}, "DB_PORT"),
        ({"DB_POOL_SIZE": 0}, "DB_POOL_SIZE"),
        ({"DB_MAX_OVERFLOW": -1}, "DB_MAX_OVERFLOW"),
        ({"DB_POOL_TIMEOUT_SECONDS": 0}, "DB_POOL_TIMEOUT_SECONDS"),
        ({"REDIS_PORT": 0}, "REDIS_PORT"),
        ({"REDIS_DB": -1}, "REDIS_DB"),
        ({"REDIS_MAX_CONNECTIONS": 0}, "REDIS_MAX_CONNECTIONS"),
        ({"REDIS_SOCKET_TIMEOUT_SECONDS": -1}, "REDIS_SOCKET_TIMEOUT_SECONDS"),
        ({"LOG_LEVEL": "LOUD"}, "LOG_LEVEL"),
    ],
)
def test_invalid_configuration_fails_fast(overrides: dict[str, object], message: str) -> None:
    settings = Settings(**overrides)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=message):
        settings.validate_startup()
