"""Local filesystem storage backend.

Suitable for a single node or a shared mount. Objects live below
:data:`Settings.FILE_STORAGE_ROOT`; every key is validated so a crafted key can
never reach a file outside the root.

This backend has no equivalent of a pre-signed URL - the process holds no secret
that a client could be trusted with - so :meth:`presign_upload` and
:meth:`presign_download` both return ``None`` and the API streams the bytes.
"""

from __future__ import annotations

import asyncio
import datetime
import os
from collections.abc import AsyncIterator
from pathlib import Path

from app.core.exceptions import ServiceUnavailableError
from app.shared.storage.content import sniff_content_type
from app.shared.storage.keys import InvalidObjectKey, validate_object_key, validate_prefix
from app.shared.storage.signer import sha256_hex
from app.shared.storage.types import ObjectContent, PresignedUpload, StoredObject

OCTET_STREAM = "application/octet-stream"


class LocalStorage:
    """Store objects below a configurable root directory."""

    provider = "local"

    def __init__(self, *, root: str | Path, bucket: str = "default") -> None:
        self._root = Path(root)
        self._bucket = bucket

    @property
    def root(self) -> Path:
        """The configured root directory."""
        return self._root

    @property
    def bucket(self) -> str:
        """The logical bucket recorded with every object."""
        return self._bucket

    def path_for(self, object_key: str) -> Path:
        """Resolve a validated key to an absolute path inside the root."""
        key = validate_object_key(object_key)
        base = self._root.resolve()
        candidate = (base / key).resolve()
        if candidate != base and base not in candidate.parents:
            raise InvalidObjectKey("object key escapes the storage root")
        return candidate

    async def put_object(
        self, *, object_key: str, data: bytes, content_type: str | None = None
    ) -> StoredObject:
        path = self.path_for(object_key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)  # noqa: ASYNC101 - one small local write

        try:
            await asyncio.to_thread(_write)
        except OSError as failure:
            raise ServiceUnavailableError(
                f"local storage write failed: {type(failure).__name__}"
            ) from failure
        return StoredObject(
            provider=self.provider,
            bucket=self._bucket,
            object_key=object_key,
            size_bytes=len(data),
            content_type=content_type or sniff_content_type(data) or OCTET_STREAM,
            etag=sha256_hex(data),
            last_modified=datetime.datetime.now(datetime.UTC),
        )

    async def get_object(self, *, object_key: str) -> ObjectContent | None:
        path = self.path_for(object_key)
        if not path.is_file():
            return None
        try:
            data = await asyncio.to_thread(path.read_bytes)
        except OSError:
            return None
        return ObjectContent(
            data=data,
            content_type=sniff_content_type(data) or OCTET_STREAM,
            size_bytes=len(data),
            etag=sha256_hex(data),
        )

    async def delete_object(self, *, object_key: str) -> bool:
        path = self.path_for(object_key)
        if not path.is_file():
            return False
        try:
            await asyncio.to_thread(path.unlink)
        except FileNotFoundError:
            return False
        except OSError as failure:
            raise ServiceUnavailableError(
                f"local storage delete failed: {type(failure).__name__}"
            ) from failure
        return True

    async def stat_object(self, *, object_key: str) -> StoredObject | None:
        path = self.path_for(object_key)

        def _stat() -> tuple[os.stat_result, bytes]:
            result = path.stat()
            with path.open("rb") as handle:
                return result, handle.read(32)

        try:
            stat, sample = await asyncio.to_thread(_stat)
        except OSError:
            return None
        return StoredObject(
            provider=self.provider,
            bucket=self._bucket,
            object_key=object_key,
            size_bytes=int(stat.st_size),
            content_type=sniff_content_type(sample) or OCTET_STREAM,
            etag=None,
            last_modified=datetime.datetime.fromtimestamp(stat.st_mtime, datetime.UTC),
        )

    async def list_objects(self, *, prefix: str) -> AsyncIterator[StoredObject]:
        wanted = validate_prefix(prefix)
        base = self._root if not wanted else self._root / wanted
        base = base.resolve()
        if not base.is_dir():
            return
        for dirpath, _dirnames, filenames in os.walk(base):
            for filename in filenames:
                path = Path(dirpath) / filename
                relative = path.relative_to(self._root.resolve()).as_posix()
                try:
                    stat = path.stat()
                    with path.open("rb") as handle:
                        sample = handle.read(32)
                except OSError:
                    continue
                yield StoredObject(
                    provider=self.provider,
                    bucket=self._bucket,
                    object_key=relative,
                    size_bytes=int(stat.st_size),
                    content_type=sniff_content_type(sample) or OCTET_STREAM,
                    etag=None,
                    last_modified=datetime.datetime.fromtimestamp(
                        stat.st_mtime, datetime.UTC
                    ),
                )

    async def presign_upload(
        self,
        *,
        object_key: str,
        content_type: str | None = None,
        expires_seconds: int = 900,
        max_size_bytes: int | None = None,
    ) -> PresignedUpload | None:
        del object_key, content_type, expires_seconds, max_size_bytes
        return None

    async def presign_download(
        self,
        *,
        object_key: str,
        filename: str | None = None,
        content_type: str | None = None,
        expires_seconds: int = 3600,
        inline: bool = False,
    ) -> str | None:
        del object_key, filename, content_type, expires_seconds, inline
        return None

    async def ensure_bucket(self) -> None:
        try:
            await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)
        except OSError as failure:
            raise ServiceUnavailableError(
                f"local storage root is unusable: {type(failure).__name__}"
            ) from failure

    async def ping(self) -> None:
        if not self._root.is_dir():
            raise ServiceUnavailableError("local storage root does not exist")
        marker = self._root / ".vctn-storage-probe"
        try:

            def _probe() -> None:
                marker.write_text("", encoding="utf-8")
                marker.unlink()

            await asyncio.to_thread(_probe)
        except OSError as failure:
            raise ServiceUnavailableError(
                f"local storage root is not writable: {type(failure).__name__}"
            ) from failure

    async def aclose(self) -> None:
        """Nothing to release: the filesystem needs no connection pool."""


__all__ = ["LocalStorage"]
