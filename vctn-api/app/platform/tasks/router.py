"""app.platform.tasks — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DbSessionDep
from app.platform.tasks.schema import ClaimResponse, TaskResponse, UserTaskResponse
from app.platform.tasks.service import TaskService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> TaskService:
    return TaskService(session)


@router.get("/tasks", response_model=ApiResponse[list[TaskResponse]])
async def list_tasks(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[list[TaskResponse]]:
    return success(await _service(session).list_tasks())


@router.get("/tasks/me", response_model=ApiResponse[list[UserTaskResponse]])
async def my_tasks(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[list[UserTaskResponse]]:
    return success(await _service(session).my_tasks(principal.subject_id))


@router.post("/tasks/{task_id}/claim", response_model=ApiResponse[ClaimResponse])
async def claim_task(
    task_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[ClaimResponse]:
    return success(await _service(session).claim(principal.subject_id, int(task_id)))
