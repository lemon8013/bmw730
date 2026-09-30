"""app.system.files — business logic.

File storage is abstract; the service records metadata and derives an opaque
``storage_key``. Mutations commit at the end of the method (transaction boundary).
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams
from app.system.files.model import SysFile
from app.system.files.repository import FileRepository, storage_key_of
from app.system.files.schema import FileCreatedResponse, FileResponse


class FileService:
    """File metadata management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = FileRepository(session)

    async def create_file(
        self,
        *,
        storage_provider: str,
        object_key: str,
        bucket: str | None = None,
        original_name: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
        checksum: str | None = None,
        owner_type: str | None = None,
        owner_id: int | None = None,
        metadata: dict | None = None,
    ) -> FileCreatedResponse:
        """Record a file's metadata and return its id and abstract storage key."""
        row = await self._repository.create(
            id=new_id(),
            storage_provider=storage_provider,
            bucket=bucket,
            object_key=object_key,
            original_name=original_name,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum=checksum,
            owner_type=owner_type,
            owner_id=owner_id,
            status="ACTIVE",
            metadata_payload=metadata,
        )
        await self._session.commit()
        return FileCreatedResponse(
            id=str(int(row.id)),
            storage_key=storage_key_of(row),
            status=row.status,
        )

    async def list_files(
        self, *, page: PageParams, status: str | None = None, owner_type: str | None = None
    ) -> Page[FileResponse]:
        rows, total = await self._repository.list_files(
            status=status, owner_type=owner_type, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_file(self, file_id: int) -> FileResponse:
        row = await self._repository.get(file_id)
        if row is None or row.status == "DELETED" or row.deleted_at is not None:
            raise NotFoundError("file not found")
        return self._to_response(row)

    async def delete_file(self, file_id: int) -> FileResponse:
        row = await self._repository.get(file_id)
        if row is None or row.status == "DELETED" or row.deleted_at is not None:
            raise NotFoundError("file not found")
        await self._repository.mark_deleted(file_id, deleted_at=datetime.datetime.now(datetime.UTC))
        await self._session.commit()
        refreshed = await self._repository.get(file_id)
        assert refreshed is not None  # kept the same row, only flagged
        return self._to_response(refreshed)

    def _to_response(self, row: SysFile) -> FileResponse:
        return FileResponse(
            id=str(int(row.id)),
            owner_type=row.owner_type,
            owner_id=None if row.owner_id is None else str(int(row.owner_id)),
            storage_provider=row.storage_provider,
            bucket=row.bucket,
            object_key=row.object_key,
            storage_key=storage_key_of(row),
            original_name=row.original_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            checksum=row.checksum,
            status=row.status,
            metadata=row.metadata_payload,
            created_at=row.created_at,
            deleted_at=row.deleted_at,
        )
