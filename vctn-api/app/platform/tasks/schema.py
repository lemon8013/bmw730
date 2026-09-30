"""app.platform.tasks — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class TaskResponse(ApiModel):
    """One task definition."""

    id: StringId
    task_code: str
    task_name: str
    task_type: str
    conditions: dict | None = None
    reward: dict | None = None
    start_at: datetime.datetime | None = None
    end_at: datetime.datetime | None = None
    repeatable: bool
    status: str


class UserTaskResponse(ApiModel):
    """One user task with its progress."""

    id: StringId
    user_id: StringId
    task_id: StringId
    task_name: str | None = None
    progress: dict | None = None
    status: str
    completed_at: datetime.datetime | None = None
    reward_claimed: bool = False
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ClaimResponse(ApiModel):
    """Result of claiming a task reward."""

    task_id: StringId
    user_task_id: OptionalStringId = None
    claimed: bool
    reward: dict | None = None
