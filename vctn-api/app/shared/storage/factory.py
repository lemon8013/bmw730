"""Backend construction for the shared object storage layer.

The factory is the only place that knows how configuration maps to a backend, so
components depend on :class:`~app.shared.storage.types.ObjectStorage` and never
on a vendor: RustFS, MinIO, Ceph RGW and AWS S3 all speak the same signed HTTP
API and all of them build the same :class:`~app.shared.storage.s3.S3Storage`.
Instances are cached per process: an S3 backend owns an httpx connection pool,
and throwing one away per request would quietly defeat it.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import ValidationError
from app.shared.storage.local import LocalStorage
from app.shared.storage.s3 import S3Storage
from app.shared.storage.types import ObjectStorage

PROVIDER_LOCAL = "local"
#: Canonical value for every S3 compatible endpoint.
PROVIDER_S3 = "s3"
#: Self documenting aliases. ``rustfs`` is what a deployment actually runs;
#: ``minio`` is kept so a configuration written before the rename still boots.
PROVIDER_RUSTFS = "rustfs"
PROVIDER_MINIO = "minio"
PROVIDERS: frozenset[str] = frozenset(
    {PROVIDER_LOCAL, PROVIDER_S3, PROVIDER_RUSTFS, PROVIDER_MINIO}
)
_S3_ALIASES: frozenset[str] = frozenset({PROVIDER_S3, PROVIDER_RUSTFS, PROVIDER_MINIO})

#: Logical bucket recorded for local objects; there is no real bucket concept.
LOCAL_BUCKET = "default"

_CACHE: dict[tuple[Any, ...], ObjectStorage] = {}


def normalize_provider(settings: Any) -> str:
    """Return ``local`` or ``s3``, collapsing every vendor alias."""
    provider = str(getattr(settings, "FILE_STORAGE_PROVIDER", PROVIDER_LOCAL)).strip().lower()
    if provider == PROVIDER_LOCAL:
        return PROVIDER_LOCAL
    if provider in _S3_ALIASES:
        return PROVIDER_S3
    raise ValidationError(f"unsupported storage provider: {provider}")


def get_object_storage(settings: Any) -> ObjectStorage:
    """Resolve the configured backend, creating it on first use."""
    provider = normalize_provider(settings)
    if provider == PROVIDER_LOCAL:
        cache_key = (PROVIDER_LOCAL, str(settings.FILE_STORAGE_ROOT))
    else:
        cache_key = (
            PROVIDER_S3,
            settings.S3_ENDPOINT,
            settings.S3_BUCKET,
            settings.S3_ACCESS_KEY,
            settings.S3_PREFIX,
            settings.S3_REGION,
            settings.S3_SECURE,
            settings.S3_ADDRESSING_STYLE,
        )

    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    backend: ObjectStorage = (
        LocalStorage(root=settings.FILE_STORAGE_ROOT, bucket=LOCAL_BUCKET)
        if provider == PROVIDER_LOCAL
        else S3Storage(
            endpoint=settings.S3_ENDPOINT,
            bucket=settings.S3_BUCKET,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION,
            secure=settings.S3_SECURE,
            prefix=settings.S3_PREFIX,
            addressing=settings.S3_ADDRESSING_STYLE,
            connect_timeout_seconds=settings.S3_CONNECT_TIMEOUT_SECONDS,
            read_timeout_seconds=settings.S3_READ_TIMEOUT_SECONDS,
            verify_tls=settings.S3_VERIFY_TLS,
            provider=PROVIDER_S3,
        )
    )
    _CACHE[cache_key] = backend
    return backend


def resolve_provider(settings: Any) -> str:
    """Return the normalized provider name (``local`` or ``s3``)."""
    return normalize_provider(settings)


def reset_object_storage_cache() -> None:
    """Drop cached backends. Tests call this when configuration changes."""
    _CACHE.clear()


__all__ = [
    "LOCAL_BUCKET",
    "PROVIDERS",
    "PROVIDER_LOCAL",
    "PROVIDER_MINIO",
    "PROVIDER_RUSTFS",
    "PROVIDER_S3",
    "get_object_storage",
    "normalize_provider",
    "reset_object_storage_cache",
    "resolve_provider",
]
