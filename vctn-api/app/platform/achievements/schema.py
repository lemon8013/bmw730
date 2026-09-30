"""app.platform.achievements — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class AchievementResponse(ApiModel):
    """One achievement definition."""

    id: StringId
    achievement_code: str
    achievement_name: str
    conditions: dict | None = None
    reward: dict | None = None
    status: str


class UserAchievementResponse(ApiModel):
    """One unlocked achievement."""

    id: StringId
    user_id: StringId
    achievement_id: StringId
    achievement_name: str | None = None
    achieved_at: datetime.datetime
