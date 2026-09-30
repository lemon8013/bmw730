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
