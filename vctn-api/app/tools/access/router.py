"""app.tools.access — HTTP endpoints.

Read endpoints resolve the access decision for a tool / caller. The management
endpoint upserts a policy row; because the access service exposes no write path it
is performed here against the session, inside the request transaction that the
session dependency commits on success.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    require_permission,
)
from app.shared.ids import new_id
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.access.model import ToolAccessPolicy
from app.tools.access.schema import AccessPolicyRequest, ToolAccessResponse
from app.tools.access.service import SUBJECT_GUEST, SUBJECT_USER, ToolAccessService

router = APIRouter()


def _service(session: DbSessionDep) -> ToolAccessService:
    # The runtime wiring injects Redis; here we resolve without it so quota
    # counters degrade to the configured defaults rather than failing the read.
    return ToolAccessService(session)


@router.get("/access/policy", response_model=ApiResponse[ToolAccessResponse])
async def access_policy(
    session: DbSessionDep,
    tool_id: str = Query(),
    subject_type: str = Query(default=SUBJECT_USER, pattern="^(GUEST|USER)$"),
) -> ApiResponse[ToolAccessResponse]:
    is_guest = subject_type == SUBJECT_GUEST
    return success(await _service(session).resolve(int(tool_id), is_guest=is_guest, ip=None))


@router.get("/access/policies", response_model=ApiResponse[list[ToolAccessResponse]])
async def access_policies(
    session: DbSessionDep,
    tool_id: str | None = Query(default=None),
) -> ApiResponse[list[ToolAccessResponse]]:
    stmt = select(ToolAccessPolicy)
    if tool_id:
        stmt = stmt.where(ToolAccessPolicy.tool_id == int(tool_id))
    stmt = stmt.order_by(ToolAccessPolicy.tool_id, ToolAccessPolicy.subject_type)
    rows = list((await session.execute(stmt)).scalars())
    return success(
        [
            ToolAccessResponse(
                tool_id=str(int(row.tool_id)),
                subject_type=str(row.subject_type),
                enabled=bool(row.enabled),
                daily_limit=None if row.daily_limit is None else int(row.daily_limit),
                used_today=0,
                remaining=None if row.daily_limit is None else int(row.daily_limit),
                rate_limit_per_minute=(
                    None if row.rate_limit_per_minute is None else int(row.rate_limit_per_minute)
                ),
                concurrency_limit=(
                    None if row.concurrency_limit is None else int(row.concurrency_limit)
                ),
            )
            for row in rows
        ]
    )


@router.put(
    "/access/policies/{tool_id}",
    response_model=ApiResponse[ToolAccessResponse],
    dependencies=[Depends(require_permission("TOOL_ACCESS_MANAGE"))],
)
async def upsert_access_policy(
    tool_id: str,
    session: DbSessionDep,
    _: AdminPrincipal,
    payload: AccessPolicyRequest,
) -> ApiResponse[ToolAccessResponse]:
    tid = int(tool_id)
    existing = await _service(session).policy_for(tid, payload.subject_type)
    if existing is None:
        existing = ToolAccessPolicy(id=new_id(), tool_id=tid, subject_type=payload.subject_type)
        session.add(existing)
    existing.enabled = payload.enabled
    existing.daily_limit = payload.daily_limit
    existing.rate_limit_per_minute = payload.rate_limit_per_minute
    existing.concurrency_limit = payload.concurrency_limit
    await session.flush()
    return success(
        ToolAccessResponse(
            tool_id=str(tid),
            subject_type=str(existing.subject_type),
            enabled=bool(existing.enabled),
            daily_limit=None if existing.daily_limit is None else int(existing.daily_limit),
            used_today=0,
            remaining=None if existing.daily_limit is None else int(existing.daily_limit),
            rate_limit_per_minute=(
                None
                if existing.rate_limit_per_minute is None
                else int(existing.rate_limit_per_minute)
            ),
            concurrency_limit=(
                None if existing.concurrency_limit is None else int(existing.concurrency_limit)
            ),
        )
    )
