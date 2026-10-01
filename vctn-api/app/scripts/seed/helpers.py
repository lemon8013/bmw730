"""Idempotent insert helpers.

The only mutation performed by the seed is an INSERT of a row whose stable
business key does not exist yet. An existing row is returned untouched, so an
administrator's later edits are never overwritten and a second run inserts
nothing.
"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id

ModelT = TypeVar("ModelT")


class SeedCounter:
    """Counts created and skipped rows per collection."""

    def __init__(self) -> None:
        self.created: dict[str, int] = {}
        self.skipped: dict[str, int] = {}

    def created_one(self, collection: str) -> None:
        """Record one inserted row."""
        self.created[collection] = self.created.get(collection, 0) + 1

    def skipped_one(self, collection: str) -> None:
        """Record one row that already existed."""
        self.skipped[collection] = self.skipped.get(collection, 0) + 1

    def total_created(self) -> int:
        return sum(self.created.values())

    def total_skipped(self) -> int:
        return sum(self.skipped.values())

    def snapshot(self) -> dict[str, dict[str, int]]:
        return {
            "created": dict(sorted(self.created.items())),
            "skipped": dict(sorted(self.skipped.items())),
        }


async def find_one(
    session: AsyncSession, model: type[ModelT], /, **equals: Any
) -> ModelT | None:
    """Return the first soft-deleted-free row matching every key, or ``None``.

    String keys are compared case-insensitively so the lookup agrees with the
    ``lower(...)`` unique indexes declared by the frozen DDL.
    """
    statement = select(model)
    for field_name, value in equals.items():
        column = getattr(model, field_name)
        if isinstance(value, str):
            statement = statement.where(func.lower(column) == value.lower())
        else:
            statement = statement.where(column == value)
    if hasattr(model, "deleted_at"):
        statement = statement.where(model.deleted_at.is_(None))
    result = await session.execute(statement)
    return result.scalars().first()


async def ensure_row(
    session: AsyncSession,
    model: type[ModelT],
    *,
    keys: dict[str, Any],
    values: dict[str, Any] | None = None,
    counter: SeedCounter | None = None,
    collection: str | None = None,
) -> tuple[ModelT, bool]:
    """Insert the row when its business key is absent, otherwise return it.

    Returns ``(row, created)``. A model that owns a surrogate ``id`` receives a
    snowflake identifier; a model with a composite primary key is inserted as
    given. ``values`` is only applied on insert and never overwrites an existing
    row.
    """
    label = collection or model.__tablename__
    existing = await find_one(session, model, **keys)
    if existing is not None:
        if counter is not None:
            counter.skipped_one(label)
        return existing, False

    payload: dict[str, Any] = dict(keys)
    payload.update(values or {})
    if hasattr(model, "id") and "id" not in payload:
        payload["id"] = new_id()
    row = model(**payload)
    session.add(row)
    await session.flush()
    if counter is not None:
        counter.created_one(label)
    return row, True


async def count_rows(session: AsyncSession, model: type[ModelT], /) -> int:
    """Return how many rows the table holds (used by integrity checks)."""
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


__all__ = ["SeedCounter", "count_rows", "ensure_row", "find_one"]
