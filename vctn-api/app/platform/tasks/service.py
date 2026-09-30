"""app.platform.tasks — business logic.

A task reacts to a business event: the event increments the progress stored in
``biz_user_task.progress`` and, once the condition is met, marks the task
completed and publishes ``TASK_COMPLETED`` so the reward is granted by the
module that owns points and growth. Claiming is idempotent: the reward is
written once, guarded by the task state itself.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.platform.growth.model import BizTask
from app.platform.points.service import PointService
from app.platform.tasks.repository import TaskRepository
from app.platform.tasks.schema import ClaimResponse, TaskResponse, UserTaskResponse
from app.shared.events.codes import OutboxEventType
from app.shared.ids import new_id
from app.shared.outbox.service import OutboxService


class TaskService:
    """Task progress, completion and reward claiming."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = TaskRepository(session)
        self._settings = settings or get_settings()
        self._outbox = OutboxService(self._settings)

    async def list_tasks(self) -> list[TaskResponse]:
        now = datetime.datetime.now(datetime.UTC)
        rows = await self._repository.active_tasks(now=now)
        return [self._to_task(row) for row in rows]

    async def my_tasks(self, user_id: int) -> list[UserTaskResponse]:
        rows = await self._repository.user_tasks(user_id)
        tasks: dict[int, BizTask] = {}
        for row in rows:
            task = await self._repository.get_task(int(row.task_id))
            if task is not None:
                tasks[int(row.task_id)] = task
        return [
            UserTaskResponse(
                id=str(int(row.id)),
                user_id=str(int(row.user_id)),
                task_id=str(int(row.task_id)),
                task_name=(
                    None if tasks.get(int(row.task_id)) is None
                    else str(tasks[int(row.task_id)].task_name)
                ),
                progress=row.progress,
                status=str(row.status),
                completed_at=row.completed_at,
                reward_claimed=bool((row.progress or {}).get("reward_claimed", False)),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def record_event(
        self,
        *,
        user_id: int,
        event_code: str,
        source_id: str | None = None,
    ) -> int:
        """Advance every task that listens to ``event_code``.

        Returns how many tasks reached completion because of this event.
        """
        now = datetime.datetime.now(datetime.UTC)
        rows = await self._repository.active_tasks(now=now)
        completed = 0
        for task in rows:
            conditions: dict[str, Any] = dict(task.conditions or {})
            if conditions.get("event_code") != event_code:
                continue
            target = int(conditions.get("target_count", 1))
            user_task = await self._repository.user_task_for_update(user_id, int(task.id))
            if user_task is None:
                user_task = await self._repository.create_user_task(
                    user_id=user_id,
                    task_id=int(task.id),
                    progress={"count": 0},
                    status="IN_PROGRESS",
                )
            if str(user_task.status) == "COMPLETED" and not bool(task.repeatable):
                continue
            progress = dict(user_task.progress or {})
            progress["count"] = int(progress.get("count", 0)) + 1
            progress["last_source_id"] = source_id
            user_task.progress = progress
            if int(progress["count"]) >= target and str(user_task.status) != "COMPLETED":
                user_task.status = "COMPLETED"
                user_task.completed_at = now
                await self._outbox.publish(
                    self._session,
                    event_type=OutboxEventType.TASK_COMPLETED,
                    aggregate_type="biz_task",
                    aggregate_id=int(task.id),
                    payload={
                        "user_id": user_id,
                        "task_id": int(task.id),
                        "task_code": str(task.task_code),
                        "reward": dict(task.reward or {}),
                        "idempotency_key": f"task:{task.id}:{user_id}:{progress['count']}",
                    },
                )
                completed += 1
            user_task.updated_at = now
            await self._session.flush()
        return completed

    async def claim(self, user_id: int, task_id: int) -> ClaimResponse:
        """Claim the reward of a completed task.

        Raises:
            BusinessRuleError: when the task is not completed, or the reward was
                already claimed.
        """
        task = await self._repository.get_task(task_id)
        if task is None:
            raise NotFoundError("task not found")
        user_task = await self._repository.user_task_for_update(user_id, task_id)
        if user_task is None or str(user_task.status) != "COMPLETED":
            raise BusinessRuleError("the task is not completed yet")

        progress = dict(user_task.progress or {})
        if bool(progress.get("reward_claimed", False)):
            raise BusinessRuleError("the reward was already claimed")
        reward: dict[str, Any] = dict(task.reward or {})

        points = int(reward.get("points", 0))
        if points:
            await PointService(self._session, self._settings).earn(
                user_id=user_id,
                points=points,
                transaction_type="EARN",
                source_type="TASK",
                source_id=str(task_id),
                reason=f"TASK:{task.task_code}",
                idempotency_key=f"task-reward:{task_id}:{user_id}",
            )
        growth_points = int(reward.get("growth_points", 0))
        if growth_points:
            from app.platform.growth.service import GrowthService

            await GrowthService(self._session, self._settings).apply_event(
                user_id=user_id,
                event_code="TASK_COMPLETED",
                growth_points=growth_points,
                source_type="TASK",
                source_id=str(task_id),
                idempotency_key=f"task-growth:{task_id}:{user_id}",
            )

        progress["reward_claimed"] = True
        user_task.progress = progress
        user_task.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._session.commit()
        return ClaimResponse(
            task_id=str(task_id),
            user_task_id=str(int(user_task.id)),
            claimed=True,
            reward=reward,
        )

    async def consume_task_completed(self, payload: dict) -> None:
        """Outbox consumer: grant a task reward without a second claim."""
        reward = dict(payload.get("reward") or {})
        points = int(reward.get("points", 0))
        if not points:
            return
        await PointService(self._session, self._settings).earn(
            user_id=int(payload["user_id"]),
            points=points,
            transaction_type="EARN",
            source_type="TASK",
            source_id=str(payload.get("task_id", "")),
            reason=f"TASK:{payload.get('task_code', '')}",
            idempotency_key=str(payload.get("idempotency_key")),
        )
        await self._session.commit()

    def _to_task(self, row: BizTask) -> TaskResponse:
        return TaskResponse(
            id=str(int(row.id)),
            task_code=str(row.task_code),
            task_name=str(row.task_name),
            task_type=str(row.task_type),
            conditions=row.conditions,
            reward=row.reward,
            start_at=row.start_at,
            end_at=row.end_at,
            repeatable=bool(row.repeatable),
            status=str(row.status),
        )


def new_task_id() -> int:
    """Expose identifier generation for tooling that seeds tasks."""
    return new_id()
