"""System health endpoints.

Mounted at the application root, outside the business API prefix:

- ``GET /health``  liveness, checks the application process only
- ``GET /ready``   readiness, checks PostgreSQL and Redis
- ``GET /version`` application name, version and environment
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.shared.database.engine import check_connection as check_database
from app.shared.redis.client import check_connection as check_redis
from app.shared.response.helper import error, success
from app.shared.response.schema import ApiError, ApiResponse

router = APIRouter(tags=["system:health"])


def _settings_of(request: Request) -> Settings:
    """Return the settings the running application was created with."""
    resolved: Settings | None = getattr(request.app.state, "settings", None)
    return resolved if resolved is not None else get_settings()


async def _probe_database(engine: AsyncEngine | None) -> dict[str, str]:
    """Probe PostgreSQL. The probe never raises: it reports the outcome."""
    if engine is None:
        return {"status": "not_configured"}
    try:
        await check_database(engine)
    except Exception as exc:  # noqa: BLE001 - a readiness probe must report any failure
        return {"status": "error", "error": type(exc).__name__}
    return {"status": "ok"}


async def _probe_redis(client: aioredis.Redis | None) -> dict[str, str]:
    """Probe Redis. The probe never raises: it reports the outcome."""
    if client is None:
        return {"status": "not_configured"}
    try:
        await check_redis(client)
    except Exception as exc:  # noqa: BLE001 - a readiness probe must report any failure
        return {"status": "error", "error": type(exc).__name__}
    return {"status": "ok"}


@router.get("/health", summary="Liveness probe")
async def health() -> ApiResponse[Any] | ApiError:
    """Liveness: verifies only that the application process is running."""
    return success({"status": "ok"})


@router.get("/ready", summary="Readiness probe")
async def ready(request: Request, response: Response) -> ApiResponse[Any] | ApiError:
    """Readiness: verifies PostgreSQL and Redis connectivity."""
    settings = _settings_of(request)
    engine: AsyncEngine | None = getattr(request.app.state, "engine", None)
    redis_client: aioredis.Redis | None = getattr(request.app.state, "redis", None)

    checks: dict[str, dict[str, str]] = {
        "postgres": await _probe_database(engine),
        "redis": await _probe_redis(redis_client),
    }
    payload: dict[str, Any] = {
        "status": "ready",
        "environment": settings.APP_ENV,
        "checks": checks,
    }

    if all(item["status"] == "ok" for item in checks.values()):
        return success(payload)

    payload["status"] = "not_ready"
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return error(
        code=ServiceUnavailableError.code,
        message=ServiceUnavailableError.message,
        data=payload,
    )


@router.get("/version", summary="Application version")
async def version(request: Request) -> ApiResponse[Any] | ApiError:
    """Return application name, version and environment."""
    settings = _settings_of(request)
    return success(
        {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        }
    )
