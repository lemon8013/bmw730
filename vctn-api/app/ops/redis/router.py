"""app.ops.redis — HTTP endpoints.

Every endpoint requires ``OPS_REDIS_VIEW`` and issues read-only informational
commands only (``PING`` / ``INFO`` / ``SLOWLOG LEN``). There is no Redis
console, and a missing or unreachable cache degrades into a structured reading
instead of an error response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import OptionalRedisDep
from app.ops.redis.schema import (
    RedisClientsResponse,
    RedisKeyspaceResponse,
    RedisMemoryResponse,
    RedisOverviewResponse,
)
from app.ops.redis.service import RedisMonitorService
from app.shared.authorization.dependencies import require_permission
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(redis: OptionalRedisDep) -> RedisMonitorService:
    return RedisMonitorService(redis)


@router.get(
    "/redis/overview",
    response_model=ApiResponse[RedisOverviewResponse],
    dependencies=[Depends(require_permission("OPS_REDIS_VIEW"))],
)
async def get_redis_overview(redis: OptionalRedisDep) -> ApiResponse[RedisOverviewResponse]:
    return success(await _service(redis).overview())


@router.get(
    "/redis/keyspace",
    response_model=ApiResponse[RedisKeyspaceResponse],
    dependencies=[Depends(require_permission("OPS_REDIS_VIEW"))],
)
async def get_redis_keyspace(redis: OptionalRedisDep) -> ApiResponse[RedisKeyspaceResponse]:
    return success(await _service(redis).keyspace())


@router.get(
    "/redis/memory",
    response_model=ApiResponse[RedisMemoryResponse],
    dependencies=[Depends(require_permission("OPS_REDIS_VIEW"))],
)
async def get_redis_memory(redis: OptionalRedisDep) -> ApiResponse[RedisMemoryResponse]:
    return success(await _service(redis).memory())


@router.get(
    "/redis/clients",
    response_model=ApiResponse[RedisClientsResponse],
    dependencies=[Depends(require_permission("OPS_REDIS_VIEW"))],
)
async def get_redis_clients(redis: OptionalRedisDep) -> ApiResponse[RedisClientsResponse]:
    return success(await _service(redis).clients())
