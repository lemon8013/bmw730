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

from app.admin.analytics.router import router as admin_analytics_router
from app.admin.audit.router import router as admin_audit_router
from app.admin.auth.router import router as admin_auth_router
from app.admin.config.router import router as admin_config_router
from app.admin.departments.router import router as admin_departments_router
from app.admin.dictionaries.router import router as admin_dictionaries_router
from app.admin.export.router import router as admin_export_router
from app.admin.growth.router import router as admin_growth_router
from app.admin.logs.router import router as admin_logs_router
from app.admin.notifications.router import router as admin_notifications_router
from app.admin.permissions.router import router as admin_permissions_router
from app.admin.roles.router import router as admin_roles_router
from app.admin.tools.router import router as admin_tools_router
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
from app.core.security_headers import AllowedHostsMiddleware, SecurityHeadersMiddleware
from app.ops.agents.router import router as ops_agents_router
from app.ops.alerts.router import router as ops_alerts_router
from app.ops.apis.router import router as ops_apis_router
from app.ops.audit.router import router as ops_audit_router
from app.ops.availability.router import router as ops_availability_router
from app.ops.dashboard.router import router as ops_dashboard_router
from app.ops.database.router import router as ops_database_router
from app.ops.events.router import router as ops_events_router
from app.ops.hosts.router import router as ops_hosts_router
from app.ops.jobs.router import router as ops_jobs_router
from app.ops.logs.router import router as ops_logs_router
from app.ops.maintenance.router import router as ops_maintenance_router
from app.ops.metrics.router import router as ops_metrics_router
from app.ops.notifications.router import router as ops_notifications_router
from app.ops.redis.router import router as ops_redis_router
from app.ops.reports.router import router as ops_reports_router
from app.ops.scheduler import build_scheduler
from app.ops.services.router import router as ops_services_router
from app.platform.achievements.router import router as platform_achievements_router
from app.platform.auth.router import router as platform_auth_router
from app.platform.cosmetics.router import router as platform_cosmetics_router
from app.platform.growth.router import router as platform_growth_router
from app.platform.levels.router import router as platform_levels_router
from app.platform.notifications.router import router as platform_notifications_router
from app.platform.points.router import router as platform_points_router
from app.platform.tasks.router import router as platform_tasks_router
from app.platform.users.router import router as platform_users_router
from app.shared.database.engine import build_engine
from app.shared.database.session import build_session_factory
from app.shared.redis.client import build_redis
from app.shared.response.helper import error
from app.shared.storage import PROVIDER_S3, get_object_storage, resolve_provider
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
    # Admin API (spec base ``/api/v1/admin``): each router already declares its
    # own business-domain segment, so the mount prefix stops at ``/admin``.
    ("/admin/auth", "admin:auth", admin_auth_router),
    ("/admin", "admin:users", admin_users_router),
    ("/admin", "admin:departments", admin_departments_router),
    ("/admin", "admin:roles", admin_roles_router),
    ("/admin", "admin:permissions", admin_permissions_router),
    ("/admin", "admin:audit", admin_audit_router),
    ("/admin", "admin:dictionaries", admin_dictionaries_router),
    ("/admin", "admin:config", admin_config_router),
    ("/admin", "admin:tools", admin_tools_router),
    ("/admin", "admin:analytics", admin_analytics_router),
    ("/admin", "admin:growth", admin_growth_router),
    ("/admin", "admin:export", admin_export_router),
    ("/admin", "admin:logs", admin_logs_router),
    ("/admin", "admin:notifications", admin_notifications_router),
    # Platform API (spec base ``/api/v1``): router paths already carry the
    # module segment (``/auth``, ``/users/me``, ``/levels`` ...).
    ("", "platform:auth", platform_auth_router),
    ("", "platform:users", platform_users_router),
    ("", "platform:growth", platform_growth_router),
    ("", "platform:points", platform_points_router),
    ("", "platform:levels", platform_levels_router),
    ("", "platform:cosmetics", platform_cosmetics_router),
    ("", "platform:notifications", platform_notifications_router),
    ("", "platform:tasks", platform_tasks_router),
    ("", "platform:achievements", platform_achievements_router),
    # Tools API (spec base ``/api/v1``).
    ("", "tools:catalog", tools_catalog_router),
    ("/tools", "tools:runtime", tools_runtime_router),
    ("/tools", "tools:access", tools_access_router),
    ("/tools", "tools:usage", tools_usage_router),
    ("/tools", "tools:statistics", tools_statistics_router),
    ("/tools", "tools:jobs", tools_jobs_router),
    # Blog API & Analytics API (spec base ``/api/v1``).
    ("/blog", "blog:articles", blog_articles_router),
    ("/blog", "blog:comments", blog_comments_router),
    ("/blog", "blog:categories", blog_categories_router),
    ("/blog", "blog:authors", blog_authors_router),
    ("/blog", "blog:interactions", blog_interactions_router),
    ("/analytics", "analytics:events", analytics_events_router),
    ("/analytics", "analytics:statistics", analytics_statistics_router),
    ("/analytics", "analytics:reports", analytics_reports_router),
    # Ops API (spec base ``/api/v1/ops``): the ops console is a separate
    # frontend, but it stays a module of this monolith — never a service.
    ("/ops", "ops:dashboard", ops_dashboard_router),
    ("/ops", "ops:hosts", ops_hosts_router),
    ("/ops", "ops:services", ops_services_router),
    ("/ops", "ops:apis", ops_apis_router),
    ("/ops", "ops:database", ops_database_router),
    ("/ops", "ops:redis", ops_redis_router),
    ("/ops", "ops:logs", ops_logs_router),
    ("/ops", "ops:metrics", ops_metrics_router),
    ("/ops", "ops:events", ops_events_router),
    ("/ops", "ops:alerts", ops_alerts_router),
    ("/ops", "ops:notifications", ops_notifications_router),
    ("/ops", "ops:agents", ops_agents_router),
    ("/ops", "ops:availability", ops_availability_router),
    ("/ops", "ops:jobs", ops_jobs_router),
    ("/ops", "ops:maintenance", ops_maintenance_router),
    ("/ops", "ops:audit", ops_audit_router),
    ("/ops", "ops:reports", ops_reports_router),
    # System API (spec base ``/api/v1``).
    ("/files", "system:files", system_files_router),
    ("/jobs", "system:jobs", system_jobs_router),
    ("/search", "system:search", system_search_router),
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
    application.state.scheduler = None
    application.state.storage = None

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

    # Object storage holds every uploaded file and generated export. The backend
    # owns a connection pool, so it is created once here and reused by every
    # request; only the S3 backend gets an eager bucket check, because a missing
    # local directory is reported by /ready rather than created behind a running
    # app.
    application.state.storage = get_object_storage(settings)
    try:
        create_bucket = (
            settings.S3_AUTO_CREATE_BUCKET
            if resolve_provider(settings) == PROVIDER_S3
            else True
        )
        if create_bucket:
            await application.state.storage.ensure_bucket()
    except Exception as failure:  # noqa: BLE001 - a boot must not crash on storage
        logger.error(
            "object storage is not ready: %s: %s", type(failure).__name__, failure
        )

    # Periodic ops work (rollups, alert evaluation, probes, retention purge)
    # runs inside this process. Every job takes an advisory lock first, so
    # additional replicas skip a tick instead of duplicating it.
    if settings.OPS_SCHEDULER_ENABLED and application.state.session_factory is not None:
        scheduler = build_scheduler(
            settings, application.state.engine, application.state.session_factory
        )
        if scheduler.start():
            application.state.scheduler = scheduler
        else:  # pragma: no cover - start() only fails here when already running
            logger.warning("ops scheduler did not start")
    elif settings.OPS_SCHEDULER_ENABLED:
        logger.warning("ops scheduler is enabled but PostgreSQL is not configured; skipped")

    logger.info(
        "application started app=%s env=%s version=%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.APP_VERSION,
    )

    try:
        yield
    finally:
        scheduler = application.state.scheduler
        if scheduler is not None:
            scheduler.shutdown()
        redis_client = application.state.redis
        if redis_client is not None:
            await redis_client.aclose()
        storage = application.state.storage
        if storage is not None:
            await storage.aclose()
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

    # Publishing the endpoint catalogue to production hands an attacker the
    # full map of every path, parameter and schema, so it is off there unless
    # somebody turns it back on deliberately.
    docs_enabled = resolved.resolved_docs_enabled
    application = FastAPI(
        title=resolved.APP_NAME,
        version=resolved.APP_VERSION,
        debug=resolved.APP_DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    # Read by the lifespan, the health endpoints and the infrastructure
    # dependencies so that every component sees the same resolved settings.
    application.state.settings = resolved

    # Starlette wraps middlewares in reverse registration order, so the list
    # below reads innermost first: the request travels bottom to top and the
    # response travels back down. The Host check sits innermost so that even
    # its rejection response is decorated with the security headers and the
    # trace identifiers added further out.
    application.add_middleware(AllowedHostsMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=resolved.CORS_ALLOW_CREDENTIALS,
        allow_methods=resolved.cors_methods,
        allow_headers=resolved.cors_headers,
        expose_headers=resolved.cors_exposed_headers,
    )
    application.add_middleware(SecurityHeadersMiddleware)
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
