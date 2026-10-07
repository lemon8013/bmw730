"""app.system.files — business logic.

Records describe objects living in the configured storage backend; the service
owns both halves - database row and stored bytes - so a successful response
always means "row exists **and** object exists". Mutations commit at the end of
the method (transaction boundary).

Upload protocol
---------------
``create_upload_intent`` reserves a key and returns either a pre-signed S3 URL
(``mode=direct``) or this API's own upload endpoint (``mode=proxy``). The
client then performs exactly one of:

* ``PUT <upload_url>`` with the returned headers, followed by ``confirm_upload``
* ``POST /files/{id}/content`` with the raw body, which writes and registers the
  object in one step

A direct upload that never arrives leaves an orphan row; ``confirm_upload``
retires it instead of pretending the file exists.
"""

from __future__ import annotations

import datetime
import hashlib
import mimetypes

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams
from app.shared.storage import ObjectStorage, get_object_storage
from app.shared.storage.content import (
    OCTET_STREAM,
    parse_allowed_mime_types,
    should_force_download,
    validate_upload,
)
from app.shared.storage.keys import build_object_key
from app.shared.storage.types import ObjectContent
from app.system.files.model import SysFile
from app.system.files.repository import FileRepository, storage_key_of
from app.system.files.schema import (
    DownloadUrlResponse,
    FileCreatedResponse,
    FileResponse,
    UploadIntentResponse,
)

DIRECT_UPLOAD_MODE = "direct"
PROXY_UPLOAD_MODE = "proxy"


class FileService:
    """File metadata and object management."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._repository = FileRepository(session)
        self._settings = settings or get_settings()
        self._storage = storage if storage is not None else get_object_storage(self._settings)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _allowed_types(self) -> frozenset[str]:
        return parse_allowed_mime_types(self._settings.FILE_ALLOWED_MIME_TYPES)

    @staticmethod
    def _parse_owner_id(value: str | int | None) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as failure:
            raise ValidationError("owner_id must be a numeric identifier") from failure

    def _resolve_declared_type(
        self, *, content_type: str | None, original_name: str | None
    ) -> str:
        """Negotiate the content type before any bytes arrive."""
        declared = (content_type or "").split(";", 1)[0].strip().lower() or None
        if declared is None and original_name:
            declared = mimetypes.guess_type(original_name)[0]
        allowed = self._allowed_types()
        if declared and allowed and declared not in allowed:
            raise ValidationError(f"content type is not allowed: {declared}")
        return declared or OCTET_STREAM

    async def _active_row(self, file_id: int) -> SysFile:
        row = await self._repository.get(file_id)
        if row is None or row.status == "DELETED" or row.deleted_at is not None:
            raise NotFoundError("file not found")
        return row

    # ------------------------------------------------------------------
    # metadata
    # ------------------------------------------------------------------
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
        row = await self._active_row(file_id)
        return self._to_response(row)

    # ------------------------------------------------------------------
    # uploads
    # ------------------------------------------------------------------
    async def create_upload_intent(
        self,
        *,
        original_name: str | None = None,
        content_type: str | None = None,
        category: str = "general",
        size_bytes: int | None = None,
        owner_type: str | None = None,
        owner_id: str | int | None = None,
        metadata: dict | None = None,
    ) -> UploadIntentResponse:
        """Reserve a key and return where the bytes must go."""
        max_bytes = self._settings.FILE_MAX_SIZE_BYTES
        if size_bytes is not None and max_bytes > 0 and size_bytes > max_bytes:
            raise ValidationError(f"file exceeds the maximum size of {max_bytes} bytes")
        resolved = self._resolve_declared_type(
            content_type=content_type, original_name=original_name
        )
        object_key = build_object_key(
            category=category,
            original_name=original_name,
            now=datetime.datetime.now(datetime.UTC),
        )
        row = await self._repository.create(
            id=new_id(),
            storage_provider=self._storage.provider,
            bucket=getattr(self._storage, "bucket", None),
            object_key=object_key,
            original_name=original_name,
            content_type=resolved,
            size_bytes=size_bytes,
            checksum=None,
            owner_type=owner_type,
            owner_id=self._parse_owner_id(owner_id),
            status="ACTIVE",
            metadata_payload=metadata,
        )
        presigned = await self._storage.presign_upload(
            object_key=object_key,
            content_type=resolved,
            expires_seconds=self._settings.FILE_PRESIGN_TTL_SECONDS,
            max_size_bytes=max_bytes,
        )
        await self._session.commit()

        if presigned is None:
            upload_url = f"{self._settings.API_PREFIX}/files/{int(row.id)}/content"
            return UploadIntentResponse(
                id=str(int(row.id)),
                mode=PROXY_UPLOAD_MODE,
                upload_url=upload_url,
                method="POST",
                headers={"Content-Type": resolved},
                expires_at=None,
                object_key=object_key,
                storage_key=storage_key_of(row),
                content_type=resolved,
                max_size_bytes=max_bytes,
            )
        return UploadIntentResponse(
            id=str(int(row.id)),
            mode=DIRECT_UPLOAD_MODE,
            upload_url=presigned.url,
            method=presigned.method,
            headers=dict(presigned.headers),
            expires_at=presigned.expires_at,
            object_key=object_key,
            storage_key=storage_key_of(row),
            content_type=resolved,
            max_size_bytes=max_bytes,
        )

    async def confirm_upload(self, file_id: int) -> FileResponse:
        """Verify a direct upload landed and record its real size."""
        row = await self._active_row(file_id)
        stored = await self._storage.stat_object(object_key=row.object_key)
        if stored is None:
            # Nothing arrived: retire the row so listings stop advertising it.
            await self._repository.mark_deleted(
                file_id, deleted_at=datetime.datetime.now(datetime.UTC)
            )
            await self._session.commit()
            raise NotFoundError("uploaded object was not found")
        await self._repository.apply_stored_object(
            file_id,
            size_bytes=stored.size_bytes,
            content_type=stored.content_type or row.content_type,
            checksum=stored.etag,
        )
        await self._session.commit()
        return self._to_response(await self._active_row(file_id))

    async def store_content(
        self, file_id: int, data: bytes, *, content_type: str | None = None
    ) -> FileResponse:
        """Write bytes through the API and update the record in one step."""
        row = await self._active_row(file_id)
        resolved = validate_upload(
            data,
            declared=content_type or row.content_type,
            allowed=self._allowed_types(),
            max_bytes=self._settings.FILE_MAX_SIZE_BYTES,
        )
        stored = await self._storage.put_object(
            object_key=row.object_key, data=data, content_type=resolved
        )
        await self._repository.apply_stored_object(
            file_id,
            size_bytes=stored.size_bytes,
            content_type=resolved,
            checksum=hashlib.sha256(data).hexdigest(),
        )
        await self._session.commit()
        return self._to_response(await self._active_row(file_id))

    # ------------------------------------------------------------------
    # downloads
    # ------------------------------------------------------------------
    async def download_url(self, file_id: int, *, inline: bool = False) -> DownloadUrlResponse:
        """Return a short lived download URL when the backend can issue one."""
        row = await self._active_row(file_id)
        content_type = row.content_type or OCTET_STREAM
        safe_inline = inline and not should_force_download(content_type)
        url = await self._storage.presign_download(
            object_key=row.object_key,
            filename=row.original_name,
            content_type=content_type,
            expires_seconds=self._settings.FILE_DOWNLOAD_URL_TTL_SECONDS,
            inline=safe_inline,
        )
        expires_at = (
            datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(seconds=self._settings.FILE_DOWNLOAD_URL_TTL_SECONDS)
            if url
            else None
        )
        return DownloadUrlResponse(
            id=str(int(row.id)),
            url=url,
            inline=safe_inline,
            expires_at=expires_at,
            content_type=content_type,
            original_name=row.original_name,
        )

    async def read_content(self, file_id: int) -> ObjectContent:
        """Read the bytes when no pre-signed URL is available."""
        row = await self._active_row(file_id)
        content = await self._storage.get_object(object_key=row.object_key)
        if content is None:
            raise NotFoundError("file content not found")
        return content

    # ------------------------------------------------------------------
    # deletion
    # ------------------------------------------------------------------
    async def delete_file(self, file_id: int) -> FileResponse:
        """Remove the stored object and then logically delete the record."""
        row = await self._active_row(file_id)
        await self._storage.delete_object(object_key=row.object_key)
        await self._repository.mark_deleted(
            file_id, deleted_at=datetime.datetime.now(datetime.UTC)
        )
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
