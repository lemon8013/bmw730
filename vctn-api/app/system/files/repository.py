"""app.system.files — data access.

Storage is abstract: the repository persists only metadata. Repositories never
commit; the service layer owns the transaction boundary.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.files.model import SysFile

STORAGE_STATUS_ACTIVE = "ACTIVE"
STORAGE_STATUS_DELETED = "DELETED"


def storage_key_of(row: SysFile) -> str:
    """Render an opaque, abstract storage location for a file record."""
    bucket = row.bucket or "default"
    return f"{row.storage_provider}://{bucket}/{row.object_key}"


class FileRepository:
    """Data access for file metadata records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysFile:
        row = SysFile(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, file_id: int) -> SysFile | None:
        return await self._session.get(SysFile, file_id)

    async def list_files(
        self, *, status: str | None, owner_type: str | None, limit: int, offset: int
    ) -> tuple[list[SysFile], int]:
        conditions = []
        if status is not None:
            conditions.append(SysFile.status == status)
        if owner_type is not None:
            conditions.append(SysFile.owner_type == owner_type)
        total = int(
            (
                await self._session.execute(
                    select(func.count(SysFile.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(SysFile)
                    .where(*conditions)
                    .order_by(SysFile.created_at.desc(), SysFile.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def mark_deleted(self, file_id: int, *, deleted_at: datetime.datetime) -> None:
        """Logically delete a file record (status + deleted_at)."""
        row = await self._session.get(SysFile, file_id)
        if row is None:
            return
        row.status = STORAGE_STATUS_DELETED
        row.deleted_at = deleted_at
        await self._session.flush()
