"""app.ops.database — HTTP endpoints.

Every endpoint requires ``OPS_DATABASE_VIEW`` and returns read-only PostgreSQL
introspection. There is no SQL console: the statements are fixed in the
repository, only their ``LIMIT`` is bound as a parameter, and a failing
collector produces a degraded reading instead of an error response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.database.schema import (
    DatabaseCacheResponse,
    DatabaseConnectionsResponse,
    DatabaseLocksResponse,
    DatabaseOverviewResponse,
    DatabaseSlowQueriesResponse,
    DatabaseStorageResponse,
    DatabaseTransactionsResponse,
)
from app.ops.database.service import DatabaseMonitorService
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import MAX_PAGE_SIZE
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> DatabaseMonitorService:
    return DatabaseMonitorService(session)


@router.get(
    "/database/overview",
    response_model=ApiResponse[DatabaseOverviewResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_overview(
    session: DbSessionDep,
) -> ApiResponse[DatabaseOverviewResponse]:
    return success(await _service(session).overview())


@router.get(
    "/database/connections",
    response_model=ApiResponse[DatabaseConnectionsResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_connections(
    session: DbSessionDep,
) -> ApiResponse[DatabaseConnectionsResponse]:
    return success(await _service(session).connections())


@router.get(
    "/database/transactions",
    response_model=ApiResponse[DatabaseTransactionsResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_transactions(
    session: DbSessionDep,
) -> ApiResponse[DatabaseTransactionsResponse]:
    return success(await _service(session).transactions())


@router.get(
    "/database/locks",
    response_model=ApiResponse[DatabaseLocksResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_locks(
    session: DbSessionDep,
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[DatabaseLocksResponse]:
    return success(await _service(session).locks(limit=limit))


@router.get(
    "/database/slow-queries",
    response_model=ApiResponse[DatabaseSlowQueriesResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_slow_queries(
    session: DbSessionDep,
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[DatabaseSlowQueriesResponse]:
    return success(await _service(session).slow_queries(limit=limit))


@router.get(
    "/database/storage",
    response_model=ApiResponse[DatabaseStorageResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_storage(
    session: DbSessionDep,
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[DatabaseStorageResponse]:
    return success(await _service(session).storage(limit=limit))


@router.get(
    "/database/cache",
    response_model=ApiResponse[DatabaseCacheResponse],
    dependencies=[Depends(require_permission("OPS_DATABASE_VIEW"))],
)
async def get_database_cache(session: DbSessionDep) -> ApiResponse[DatabaseCacheResponse]:
    return success(await _service(session).cache())
