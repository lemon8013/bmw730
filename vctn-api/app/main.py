"""VCTN unified FastAPI application (Phase 0 skeleton).

Single modular monolith: every business module is mounted into this one
application. There is no second backend, and modules must never call each other
over HTTP.

Business endpoints live under ``API_PREFIX`` (``/api/v1``). System probes live at
the application root.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.admin.audit.router import router as admin_audit_router
from app.admin.auth.router import router as admin_auth_router
from app.admin.config.router import router as admin_config_router
from app.admin.departments.router import router as admin_departments_router
from app.admin.dictionaries.router import router as admin_dictionaries_router
from app.admin.permissions.router import router as admin_permissions_router
from app.admin.roles.router import router as admin_roles_router
from app.admin.users.router import router as admin_users_router
from app.analytics.events.router import router as analytics_events_router
from app.analytics.reports.router import router as analytics_reports_router
from app.analytics.statistics.router import router as analytics_statistics_router
from app.blog.articles.router import router as blog_articles_router
from app.blog.authors.router import router as blog_authors_router
from app.blog.categories.router import router as blog_categories_router
from app.blog.comments.router import router as blog_comments_router
from app.blog.interactions.router import router as blog_interactions_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppException, ValidationError
from app.core.logging import get_logger, setup_logging
from app.core.middleware import TraceContextMiddleware
from app.platform.auth.router import router as platform_auth_router
from app.platform.cosmetics.router import router as platform_cosmetics_router
from app.platform.growth.router import router as platform_growth_router
from app.platform.levels.router import router as platform_levels_router
from app.platform.notifications.router import router as platform_notifications_router
from app.platform.points.router import router as platform_points_router
from app.platform.users.router import router as platform_users_router
from app.shared.database.engine import build_engine
from app.shared.database.session import build_session_factory
from app.shared.redis.client import build_redis
from app.shared.response.helper import error
from app.system.files.router import router as system_files_router
from app.system.health.router import router as system_health_router
from app.system.jobs.router import router as system_jobs_router
from app.system.search.router import router as system_search_router
from app.tools.access.router import router as tools_access_router
from app.tools.catalog.router import router as tools_catalog_router
from app.tools.jobs.router import router as tools_jobs_router
from app.tools.runtime.router import router as tools_runtime_router
from app.tools.statistics.router import router as tools_statistics_router
from app.tools.usage.router import router as tools_usage_router

_BUSINESS_ROUTERS: Final[tuple[tuple[str, str, APIRouter], ...]] = (
    ("/admin/auth", "admin:auth", admin_auth_router),
    ("/admin/users", "admin:users", admin_users_router),
    ("/admin/departments", "admin:departments", admin_departments_router),
    ("/admin/roles", "admin:roles", admin_roles_router),
    ("/admin/permissions", "admin:permissions", admin_permissions_router),
    ("/admin/audit", "admin:audit", admin_audit_router),
    ("/admin/dictionaries", "admin:dictionaries", admin_dictionaries_router),
    ("/admin/config", "admin:config", admin_config_router),
    ("/platform/auth", "platform:auth", platform_auth_router),
    ("/platform/users", "platform:users", platform_users_router),
    ("/platform/growth", "platform:growth", platform_growth_router),
    ("/platform/points", "platform:points", platform_points_router),
    ("/platform/levels", "platform:levels", platform_levels_router),
    ("/platform/cosmetics", "platform:cosmetics", platform_cosmetics_router),
    ("/platform/notifications", "platform:notifications", platform_notifications_router),
    ("/tools/catalog", "tools:catalog", tools_catalog_router),
    ("/tools/runtime", "tools:runtime", tools_runtime_router),
    ("/tools/access", "tools:access", tools_access_router),
    ("/tools/usage", "tools:usage", tools_usage_router),
    ("/tools/statistics", "tools:statistics", tools_statistics_router),
    ("/tools/jobs", "tools:jobs", tools_jobs_router),
    ("/blog/articles", "blog:articles", blog_articles_router),
    ("/blog/comments", "blog:comments", blog_comments_router),
    ("/blog/categories", "blog:categories", blog_categories_router),
    ("/blog/authors", "blog:authors", blog_authors_router),
    ("/blog/interactions", "blog:interactions", blog_interactions_router),
    ("/analytics/events", "analytics:events", analytics_events_router),
    ("/analytics/statistics", "analytics:statistics", analytics_statistics_router),
    ("/analytics/reports", "analytics:reports", analytics_reports_router),
    ("/system/files", "system:files", system_files_router),
    ("/system/jobs", "system:jobs", system_jobs_router),
    ("/system/search", "system:search", system_search_router),
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Bind and release infrastructure resources around the app lifetime."""
    settings: Settings = application.state.settings
    settings.validate_startup()
    setup_logging(settings)
    logger = get_logger()

    application.state.engine = None
    application.state.session_factory = None
    application.state.redis = None

    if settings.is_database_configured:
        engine = build_engine(settings)
        application.state.engine = engine
        application.state.session_factory = build_session_factory(engine)
    else:
        missing = settings.missing_database_fields
        if missing:
            logger.warning(
                "PostgreSQL configuration is incomplete; missing: %s. Database access is disabled",
                ", ".join(missing),
            )
        else:
            logger.warning("PostgreSQL is not configured; database access is disabled")

    if settings.is_redis_configured:
        application.state.redis = build_redis(settings)
    else:
        logger.warning("Redis is not configured; redis access is disabled")

    logger.info(
        "application started app=%s env=%s version=%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.APP_VERSION,
    )

    try:
        yield
    finally:
        redis_client = application.state.redis
        if redis_client is not None:
            await redis_client.aclose()
        engine = application.state.engine
        if engine is not None:
            await engine.dispose()
        logger.info("application stopped")


def _register_exception_handlers(application: FastAPI) -> None:
    """Map every exception to the unified response envelope."""

    @application.exception_handler(AppException)
    async def _handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error(code=exc.code, message=exc.message, data=exc.data).model_dump(),
        )

    @application.exception_handler(RequestValidationError)
    async def _handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        failure = ValidationError()
        # Only loc/type/msg are surfaced: raw input values are never echoed back.
        details = [
            {
                "loc": [str(part) for part in item.get("loc", ())],
                "type": str(item.get("type", "")),
                "msg": str(item.get("msg", "")),
            }
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=failure.http_status,
            content=error(
                code=failure.code,
                message=failure.message,
                data={"errors": details},
            ).model_dump(),
        )

    @application.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(
                code=exc.status_code * 1000 + 1,
                message=str(exc.detail),
            ).model_dump(),
        )

    @application.exception_handler(Exception)
    async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        get_logger().error("unhandled application error type=%s", type(exc).__name__)
        failure = AppException()
        return JSONResponse(
            status_code=failure.http_status,
            content=error(code=failure.code, message=failure.message).model_dump(),
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the single VCTN FastAPI application."""
    resolved = settings or get_settings()
    resolved.validate_startup()

    application = FastAPI(
        title=resolved.APP_NAME,
        version=resolved.APP_VERSION,
        debug=resolved.APP_DEBUG,
        lifespan=lifespan,
    )
    # Read by the lifespan, the health endpoints and the infrastructure
    # dependencies so that every component sees the same resolved settings.
    application.state.settings = resolved

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=resolved.CORS_ALLOW_CREDENTIALS,
        allow_methods=resolved.cors_methods,
        allow_headers=resolved.cors_headers,
        expose_headers=resolved.cors_exposed_headers,
    )
    application.add_middleware(TraceContextMiddleware)

    application.include_router(system_health_router)

    for path, tag, module_router in _BUSINESS_ROUTERS:
        application.include_router(
            module_router,
            prefix=f"{resolved.API_PREFIX}{path}",
            tags=[tag],
        )

    _register_exception_handlers(application)
    return application


app = create_app()
