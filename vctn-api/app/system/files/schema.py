"""app.system.files — request and response DTOs.

File storage is abstract: the module records only metadata and a derived
``storage_key`` (an opaque location string). No binary content is ever read or
written to disk or to a cloud provider.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class FileCreateRequest(ApiModel):
    """Record file metadata; storage is abstract (no real binary I/O)."""

    storage_provider: str = "ABSTRACT"
    bucket: str | None = None
    object_key: str
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    owner_type: str | None = None
    owner_id: int | None = None
    metadata: dict[str, Any] | None = None


class FileResponse(ApiModel):
    """A file metadata record."""

    id: StringId
    owner_type: str | None = None
    owner_id: OptionalStringId = None
    storage_provider: str
    bucket: str | None = None
    object_key: str
    storage_key: str
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    status: str
    metadata: dict[str, Any] | None = None
    created_at: datetime.datetime
    deleted_at: datetime.datetime | None = None


class FileCreatedResponse(ApiModel):
    """Result of recording a file."""

    id: StringId
    storage_key: str
    status: str
