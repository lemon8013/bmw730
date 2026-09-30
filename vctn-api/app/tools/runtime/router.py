"""app.tools.runtime — HTTP endpoints.

A single execution endpoint. The router only resolves the caller and delegates to
:class:`app.tools.runtime.service.ToolRuntimeService`, which owns the entire
frozen execution order (resolve subject -> risk -> access -> quota -> rate limit ->
provider lookup by component_key -> usage). Dispatch is never performed here.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.dependencies import DbSessionDep, OptionalRedisDep
from app.core.logging import get_logger
from app.shared.authorization.dependencies import OptionalPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.runtime.schema import ToolExecuteRequest, ToolExecuteResponse
from app.tools.runtime.service import ToolRuntimeService, redact_inputs

router = APIRouter()
logger = get_logger(__name__)


@router.post("/runtime/execute/{tool_id}", response_model=ApiResponse[ToolExecuteResponse])
async def execute_tool(
    tool_id: str,
    body: ToolExecuteRequest,
    session: DbSessionDep,
    redis: OptionalRedisDep,
    principal: OptionalPrincipal,
    request: Request,
) -> ApiResponse[ToolExecuteResponse]:
    user_id = principal.subject_id if principal is not None else None
    ip = (
        principal.ip
        if principal is not None
        else (request.client.host if request.client else None)
    )
    user_agent = (
        principal.user_agent
        if principal is not None
        else request.headers.get("user-agent")
    )

    # Raw inputs are never logged; only a redacted, masked view reaches the log.
    logger.info(
        "tool.execute requested tool_id=%s subject=%s inputs=%s",
        tool_id,
        "guest" if user_id is None else f"user:{user_id}",
        redact_inputs(body.inputs),
    )

    result = await ToolRuntimeService(session, redis=redis).execute(
        int(tool_id),
        inputs=body.inputs,
        user_id=user_id,
        anonymous_id=body.anonymous_id,
        ip=ip,
        user_agent=user_agent,
    )
    return success(result)
