"""app.admin.growth — data access.

Only the queries that the operator-facing contract needs **and** that no
platform repository already provides live here. Everything else (ledger paging,
account locks, level recalculation) is delegated to the owning module so the
accounting rules stay single-sourced.
"""

from __future__ import annotations

import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.growth.model import BizTask, BizUserTask
from app.platform.users.model import BizUser
from app.shared.ids import new_id

SOFT_DELETED_NULL = "soft-deleted rows stay readable for audit purposes"


class AdminGrowthRepository:
    """Read queries that the administrative gamification surface needs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Business users
    # ------------------------------------------------------------------
    async def get_biz_user(self, user_id: int) -> BizUser | None:
        return await self._session.get(BizUser, user_id)

    async def list_biz_users(
        self, *, keyword: str | None, status: str | None, limit: int, offset: int
    ) -> tuple[list[BizUser], int]:
        conditions: list[object] = []
        if status:
            conditions.append(BizUser.status == status)
        if keyword:
            pattern = f"%{keyword.lower()}%"
            conditions.append(
                or_(
                    func.lower(BizUser.username).like(pattern),
                    func.lower(BizUser.nickname).like(pattern),
                    func.lower(BizUser.email).like(pattern),
                )
            )
        where = and_(*conditions) if conditions else None
        count_stmt = select(func.count(BizUser.id))
        page_stmt = (
            select(BizUser)
            .order_by(BizUser.registered_at.desc(), BizUser.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if where is not None:
            count_stmt = count_stmt.where(where)
            page_stmt = page_stmt.where(where)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        rows = (await self._session.execute(page_stmt)).scalars().all()
        return list(rows), total

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    async def user_tasks_with_definition(
        self, user_id: int
    ) -> list[tuple[BizUserTask, BizTask | None]]:
        """User tasks joined with their definition; the definition may be gone."""
        rows = await self._session.execute(
            select(BizUserTask, BizTask)
            .outerjoin(BizTask, BizTask.id == BizUserTask.task_id)
            .where(BizUserTask.user_id == user_id)
            .order_by(BizUserTask.updated_at.desc(), BizUserTask.id.desc())
        )
        return [(user_task, task) for user_task, task in rows.all()]

    async def task_usage_count(self, task_id: int) -> int:
        """How many users already progressed on a task."""
        return int(
            (
                await self._session.execute(
                    select(func.count(BizUserTask.id)).where(BizUserTask.task_id == task_id)
                )
            ).scalar_one()
        )

    # ------------------------------------------------------------------
    # Task definitions (CRUD)
    # ------------------------------------------------------------------
    async def list_tasks(self, *, include_disabled: bool) -> list[BizTask]:
        stmt = select(BizTask).where(BizTask.deleted_at.is_(None))
        if not include_disabled:
            stmt = stmt.where(BizTask.status == "ACTIVE")
        return list((await self._session.execute(stmt.order_by(BizTask.id))).scalars())

    async def get_task(self, task_id: int) -> BizTask | None:
        result = await self._session.execute(
            select(BizTask).where(BizTask.id == task_id, BizTask.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def task_code_taken(self, task_code: str, *, exclude_id: int | None = None) -> bool:
        stmt = select(func.count(BizTask.id)).where(
            func.lower(BizTask.task_code) == task_code.lower(),
            BizTask.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(BizTask.id != exclude_id)
        return int((await self._session.execute(stmt)).scalar_one()) > 0

    async def create_task(self, **fields: object) -> BizTask:
        row = BizTask(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def soft_delete_task(self, row: BizTask) -> None:
        """Retire a task definition.

        Only ever soft-deleted: users keep progress rows pointing at it, so a
        physical delete would break their history (and the foreign key).
        """
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Growth & point rules (CRUD)
    # ------------------------------------------------------------------
    async def create_rule(self, model: type, **fields: object) -> object:
        row = model(id=new_id(), **fields)  # type: ignore[call-arg]
        self._session.add(row)
        await self._session.flush()
        return row

    async def rule_code_taken(
        self, model: type, rule_code: str, *, exclude_id: int | None = None
    ) -> bool:
        stmt = select(func.count(model.id)).where(  # type: ignore[attr-defined]
            func.lower(model.rule_code) == rule_code.lower(),  # type: ignore[attr-defined]
            model.deleted_at.is_(None),  # type: ignore[attr-defined]
        )
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)  # type: ignore[attr-defined]
        return int((await self._session.execute(stmt)).scalar_one()) > 0

    async def soft_delete_rule(self, row: object) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)  # type: ignore[attr-defined]
        await self._session.flush()

    # ------------------------------------------------------------------
    # Levels (CRUD)
    # ------------------------------------------------------------------
    async def create_level(self, **fields: object) -> object:
        from app.platform.levels.model import BizUserLevel

        row = BizUserLevel(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def level_code_taken(self, level_code: str, *, exclude_id: int | None = None) -> bool:
        from app.platform.levels.model import BizUserLevel

        stmt = select(func.count(BizUserLevel.id)).where(
            func.lower(BizUserLevel.level_code) == level_code.lower(),
            BizUserLevel.deleted_at.is_(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(BizUserLevel.id != exclude_id)
        return int((await self._session.execute(stmt)).scalar_one()) > 0

    async def level_usage_count(self, level_id: int) -> int:
        from app.platform.growth.model import BizUserGrowthAccount
        from app.platform.levels.model import BizUserLevelHistory

        accounts = await self.count_rows_where(
            BizUserGrowthAccount,
            BizUserGrowthAccount.current_level_id == level_id,
            column=BizUserGrowthAccount.user_id,
        )
        history = await self.count_rows_where(
            BizUserLevelHistory,
            or_(
                BizUserLevelHistory.to_level_id == level_id,
                BizUserLevelHistory.from_level_id == level_id,
            ),
        )
        return accounts + history

    async def soft_delete_level(self, row: object) -> None:
        """Retire a level.

        Levels are only ever soft-deleted: ``biz_user_growth_account`` holds a
        foreign key to them, so a physical delete would be rejected even when no
        user is on the level any more. Retiring keeps past level changes
        readable.
        """
        from app.platform.levels.model import BizUserLevel

        assert isinstance(row, BizUserLevel)
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Achievements & cosmetics (per user)
    # ------------------------------------------------------------------
    async def all_achievements(self) -> list[object]:
        from app.platform.growth.model import BizAchievement

        rows = await self._session.execute(
            select(BizAchievement)
            .where(BizAchievement.deleted_at.is_(None))
            .order_by(BizAchievement.id)
        )
        return list(rows.scalars())

    async def unlocked_map(self, user_id: int) -> dict[int, datetime.datetime]:
        from app.platform.growth.model import BizUserAchievement

        rows = await self._session.execute(
            select(BizUserAchievement).where(BizUserAchievement.user_id == user_id)
        )
        return {
            int(row.achievement_id): row.achieved_at
            for row in rows.scalars()
            if row.achievement_id is not None
        }

    async def all_cosmetics(self) -> list[object]:
        from app.platform.cosmetics.model import BizCosmetic

        rows = await self._session.execute(
            select(BizCosmetic)
            .where(BizCosmetic.deleted_at.is_(None))
            .order_by(BizCosmetic.sort_order, BizCosmetic.id)
        )
        return list(rows.scalars())

    async def owned_map(self, user_id: int) -> dict[int, tuple[object, object]]:
        from app.platform.cosmetics.model import BizUserCosmetic

        rows = await self._session.execute(
            select(BizUserCosmetic).where(BizUserCosmetic.user_id == user_id)
        )
        return {
            int(row.cosmetic_id): (row.obtained_at, row.source_type)
            for row in rows.scalars()
            if row.cosmetic_id is not None
        }

    async def equipment(self, user_id: int) -> object | None:
        from app.platform.cosmetics.model import BizUserEquipment

        return await self._session.get(BizUserEquipment, user_id)

    async def level_history(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[object], int]:
        from app.platform.levels.model import BizUserLevelHistory

        total = await self.count_rows_where(
            BizUserLevelHistory, BizUserLevelHistory.user_id == user_id
        )
        rows = await self._session.execute(
            select(BizUserLevelHistory)
            .where(BizUserLevelHistory.user_id == user_id)
            .order_by(BizUserLevelHistory.created_at.desc(), BizUserLevelHistory.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars()), total

    # ------------------------------------------------------------------
    # Overview counters
    # ------------------------------------------------------------------
    async def count_rows(self, model: type, *, column: object | None = None) -> int:
        """Count every row of ``model``.

        ``column`` overrides what is counted for tables keyed by something other
        than ``id`` (``biz_user_growth_account`` and ``biz_user_point_account``
        are both keyed by ``user_id``).
        """
        target = column if column is not None else model.id  # type: ignore[attr-defined]
        return int((await self._session.execute(select(func.count(target)))).scalar_one())

    async def count_rows_where(
        self, model: type, *conditions: object, column: object | None = None
    ) -> int:
        """Count rows matching ``conditions``.

        ``column`` selects what to count: most tables have an ``id`` primary key,
        but ``biz_user_growth_account`` is keyed by ``user_id``, so the caller has
        to be able to say so instead of every table pretending to have ``id``.
        """
        target = column if column is not None else model.id  # type: ignore[attr-defined]
        stmt = select(func.count(target)).where(*conditions)
        return int((await self._session.execute(stmt)).scalar_one())

    async def sum_column(self, column: object) -> int:
        stmt = select(func.coalesce(func.sum(column), 0))
        value = (await self._session.execute(stmt)).scalar_one()
        return int(value)
