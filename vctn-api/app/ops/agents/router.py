"""app.ops.agents — HTTP endpoints.

Read endpoints require ``OPS_AGENT_VIEW``; registration and enablement require
``OPS_AGENT_MANAGE``. ``POST /agents/heartbeat`` is the one exception: it is
called by the agent itself, which has no admin session, so it carries its own
credential (in the body or in the ``X-Agent-Code`` / ``X-Agent-Token`` headers)
instead of a permission.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request

from app.core.dependencies import DbSessionDep
from app.ops.agents.schema import (
    DEFAULT_HEARTBEAT_WINDOW_HOURS,
    MAX_HEARTBEAT_WINDOW_HOURS,
    AgentCreateRequest,
    AgentHeartbeatAcceptedResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegisterResponse,
    AgentResponse,
)
from app.ops.agents.service import AgentService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AgentService:
    return AgentService(session)


@router.get(
    "/agents",
    response_model=ApiResponse[Page[AgentResponse]],
    dependencies=[Depends(require_permission("OPS_AGENT_VIEW"))],
)
async def list_agents(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AgentResponse]]:
    return success(
        await _service(session).list_agents(
            keyword=keyword,
            status=status,
            enabled=enabled,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/agents/{agent_id}",
    response_model=ApiResponse[AgentResponse],
    dependencies=[Depends(require_permission("OPS_AGENT_VIEW"))],
)
async def get_agent(agent_id: str, session: DbSessionDep) -> ApiResponse[AgentResponse]:
    return success(await _service(session).get_agent(int(agent_id)))


@router.post(
    "/agents",
    response_model=ApiResponse[AgentRegisterResponse],
    dependencies=[Depends(require_permission("OPS_AGENT_MANAGE"))],
)
async def register_agent(
    payload: AgentCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AgentRegisterResponse]:
    return success(await _service(session).register_agent(principal, payload))


@router.post(
    "/agents/{agent_id}/enable",
    response_model=ApiResponse[AgentResponse],
    dependencies=[Depends(require_permission("OPS_AGENT_MANAGE"))],
)
async def enable_agent(
    agent_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[AgentResponse]:
    return success(
        await _service(session).set_agent_enabled(principal, int(agent_id), enabled=True)
    )


@router.post(
    "/agents/{agent_id}/disable",
    response_model=ApiResponse[AgentResponse],
    dependencies=[Depends(require_permission("OPS_AGENT_MANAGE"))],
)
async def disable_agent(
    agent_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[AgentResponse]:
    return success(
        await _service(session).set_agent_enabled(principal, int(agent_id), enabled=False)
    )


@router.post(
    "/agents/heartbeat",
    response_model=ApiResponse[AgentHeartbeatAcceptedResponse],
)
async def report_heartbeat(
    request: Request,
    payload: AgentHeartbeatRequest,
    session: DbSessionDep,
    x_agent_code: str | None = Header(default=None),
    x_agent_token: str | None = Header(default=None),
) -> ApiResponse[AgentHeartbeatAcceptedResponse]:
    return success(
        await _service(session).record_heartbeat(
            payload,
            header_agent_code=x_agent_code,
            header_token=x_agent_token,
            client_ip=request.client.host if request.client else None,
        )
    )


@router.get(
    "/agents/{agent_id}/heartbeats",
    response_model=ApiResponse[Page[AgentHeartbeatResponse]],
    dependencies=[Depends(require_permission("OPS_AGENT_VIEW"))],
)
async def list_heartbeats(
    agent_id: str,
    session: DbSessionDep,
    hours: int = Query(
        default=DEFAULT_HEARTBEAT_WINDOW_HOURS, ge=1, le=MAX_HEARTBEAT_WINDOW_HOURS
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AgentHeartbeatResponse]]:
    return success(
        await _service(session).list_heartbeats(
            int(agent_id),
            hours=hours,
            page=PageParams(page=page, page_size=page_size),
        )
    )
