"""app.platform.levels — business logic."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.platform.growth.repository import GrowthRepository
from app.platform.levels.model import BizUserLevel
from app.platform.levels.repository import LevelRepository
from app.platform.levels.schema import (
    LevelBenefitResponse,
    LevelHistoryResponse,
    LevelResponse,
    MyLevelResponse,
)
from app.shared.pagination.params import Page, PageParams


class LevelService:
    """Level definitions and the level state of a business user."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = LevelRepository(session)
        self._growth = GrowthRepository(session)
        self._settings = settings or get_settings()

    async def list_levels(self) -> list[LevelResponse]:
        """Return every level definition (public information)."""
        rows = await self._repository.list_levels()
        return [self._to_response(row) for row in rows]

    async def my_level(self, user_id: int) -> MyLevelResponse:
        """Return the caller's level, its progress and its benefits."""
        account = await self._growth.account(user_id) or await self._growth.create_account(user_id)
        levels = await self._repository.list_levels()
        total = int(account.total_growth_points or 0)
        current = _by_id(levels, account.current_level_id)
        next_level = _next(levels, total)
        benefits: list[LevelBenefitResponse] = []
        if current is not None:
            benefits = [
                LevelBenefitResponse(
                    id=str(int(row.id)),
                    level_id=str(int(row.level_id)),
                    benefit_type=str(row.benefit_type),
                    benefit_code=str(row.benefit_code),
                    benefit_value=row.benefit_value,
                    enabled=bool(row.enabled),
                )
                for row in await self._repository.enabled_benefits_of(int(current.id))
            ]
        return MyLevelResponse(
            user_id=str(user_id),
            total_growth_points=total,
            current_level=None if current is None else self._to_response(current),
            next_level=None if next_level is None else self._to_response(next_level),
            points_to_next_level=(
                None if next_level is None else int(next_level.min_growth_points) - total
            ),
            benefits=benefits,
        )

    async def history(self, user_id: int, *, page: PageParams) -> Page[LevelHistoryResponse]:
        rows = await self._repository.history_of(user_id, limit=page.limit)
        return Page.build(
            items=[
                LevelHistoryResponse(
                    id=str(int(row.id)),
                    user_id=str(int(row.user_id)),
                    from_level_id=None
                    if row.from_level_id is None
                    else str(int(row.from_level_id)),
                    to_level_id=None if row.to_level_id is None else str(int(row.to_level_id)),
                    growth_points=int(row.growth_points),
                    reason=row.reason,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=len(rows),
            params=page,
        )

    def _to_response(self, row: BizUserLevel) -> LevelResponse:
        return LevelResponse(
            id=str(int(row.id)),
            level_code=str(row.level_code),
            level_name=str(row.level_name),
            level_no=int(row.level_no),
            min_growth_points=int(row.min_growth_points),
            max_growth_points=(
                None if row.max_growth_points is None else int(row.max_growth_points)
            ),
            icon_url=row.icon_url,
            description=row.description,
            status=str(row.status),
            sort_order=int(row.sort_order or 0),
        )


def _by_id(levels: list[BizUserLevel], level_id: object | None) -> BizUserLevel | None:
    if level_id is None:
        return None
    for row in levels:
        if int(row.id) == int(level_id):  # type: ignore[arg-type]
            return row
    return None


def _next(levels: list[BizUserLevel], points: int) -> BizUserLevel | None:
    for row in levels:
        if int(row.min_growth_points) > points:
            return row
    return None
