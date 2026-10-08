"""S3 compatible object storage backend (RustFS, MinIO, Ceph RGW, AWS S3).

Implemented directly against the S3 REST API because the dependency index
allows exactly one HTTP client - ``httpx`` - and therefore no S3 SDK. Signature
Version 4 is computed in :mod:`app.shared.storage.signer`.

Design notes that matter in production:

* **No streaming.** Objects are expected to be small (avatars, screenshots,
  generated reports) and are read into memory. Multipart uploads are not
  implemented; raise the size limit instead of uploading gigabytes.
* **No automatic retries beyond one attempt.** A retry of a non-idempotent
  write is worse than a visible failure, so only transport level errors are
  retried once; HTTP status codes are surfaced immediately.
* **The endpoint is trusted infrastructure.** Listing parses XML returned by the
  object store, whose address comes from the operator's own configuration.
"""

from __future__ import annotations

import datetime
import email.utils
import xml.etree.ElementTree as ElementTree
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote

import httpx

from app.core.exceptions import ServiceUnavailableError
from app.shared.storage.content import should_force_download
from app.shared.storage.keys import validate_object_key, validate_prefix
from app.shared.storage.signer import (
    canonical_query,
    canonical_uri,
    presign,
    sha256_hex,
    sign_request,
)
from app.shared.storage.types import ObjectContent, PresignedUpload, StoredObject

_NAMESPACE = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"
_NOT_FOUND = 404


class S3Storage:
    """Talk to an S3 compatible endpoint."""

    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        secure: bool = True,
        prefix: str = "",
        addressing: str = "path",
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 30.0,
        verify_tls: bool = True,
        provider: str = "s3",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        scheme, host = _split_endpoint(endpoint, secure=secure)
        self._bucket = bucket
        self._region = region
        self._access_key = access_key
        self._secret_key = secret_key
        self._prefix = (prefix or "").strip().strip("/")
        self._addressing = "virtual" if addressing.strip().lower() == "virtual" else "path"
        self.provider = provider
        if self._addressing == "virtual":
            self._base_url = f"{scheme}://{bucket}.{host}"
            self._bucket_prefix = ""
        else:
            self._base_url = f"{scheme}://{host}"
            self._bucket_prefix = f"/{bucket}"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=read_timeout_seconds,
                pool=connect_timeout_seconds,
            ),
            verify=verify_tls,
            transport=transport,
        )

    # ------------------------------------------------------------------
    # key handling
    # ------------------------------------------------------------------
    @property
    def bucket(self) -> str:
        """The bucket every object of this backend lives in."""
        return self._bucket

    def full_key(self, object_key: str) -> str:
        """Return the stored key, including the configured global prefix."""
        key = validate_object_key(object_key)
        return f"{self._prefix}/{key}" if self._prefix else key

    def _uri_of(self, stored_key: str) -> str:
        return f"{self._bucket_prefix}/{stored_key}"

    def _target(self, stored_key: str) -> tuple[str, str]:
        """Return ``(uri, absolute url)`` for a stored key."""
        uri = self._uri_of(stored_key)
        return uri, f"{self._base_url}{canonical_uri(uri)}"

    # ------------------------------------------------------------------
    # signed requests
    # ------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        stored_key: str = "",
        *,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        data: bytes = b"",
        allow_missing: bool = False,
    ) -> httpx.Response | None:
        """Execute one signed request. ``None`` means "the object is absent"."""
        uri, base = self._target(stored_key) if stored_key else (
            self._bucket_prefix,
            f"{self._base_url}{canonical_uri(self._bucket_prefix)}" if self._bucket_prefix
            else self._base_url,
        )
        payload_hash = sha256_hex(data)
        signed = dict(headers or {})
        signed["host"] = self._host()
        signed["x-amz-content-sha256"] = payload_hash
        authorization, amzdate = sign_request(
            method=method,
            uri=uri,
            query=query,
            headers=signed,
            payload_hash=payload_hash,
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
            moment=datetime.datetime.now(datetime.UTC),
        )
        signed["authorization"] = authorization
        signed["x-amz-date"] = amzdate
        url = base if not query else f"{base}?{canonical_query(query)}"

        response = await self._send(method, url, headers=signed, data=data)
        if response.status_code == _NOT_FOUND and allow_missing:
            return None
        if response.status_code >= 400:
            raise ServiceUnavailableError(
                f"object storage rejected {method} with {response.status_code}: "
                f"{_brief(response.text)}"
            )
        return response

    async def _send(
        self, method: str, url: str, *, headers: dict[str, str], data: bytes
    ) -> httpx.Response:
        try:
            return await self._client.request(
                method, url, content=data, headers=headers
            )
        except httpx.HTTPError:
            # One retry: a pooled connection dropped by the load balancer is
            # common enough to be worth absorbing, anything else must surface.
            try:
                return await self._client.request(
                    method, url, content=data, headers=headers
                )
            except httpx.HTTPError as retry_failure:
                raise ServiceUnavailableError(
                    f"object storage is unreachable: {type(retry_failure).__name__}"
                ) from retry_failure
        except httpx.TransportError as failure:  # pragma: no cover - covered above
            raise ServiceUnavailableError(
                f"object storage is unreachable: {type(failure).__name__}"
            ) from failure

    def _host(self) -> str:
        stripped = self._base_url
        for prefix in ("https://", "http://"):
            if stripped.startswith(prefix):
                return stripped[len(prefix) :].rstrip("/")
        return stripped.rstrip("/")

    # ------------------------------------------------------------------
    # ObjectStorage implementation
    # ------------------------------------------------------------------
    async def put_object(
        self, *, object_key: str, data: bytes, content_type: str | None = None
    ) -> StoredObject:
        stored = self.full_key(object_key)
        headers = {"content-type": content_type or "application/octet-stream"}
        response = await self._request("PUT", stored, headers=headers, data=data)
        assert response is not None  # a write never yields "missing"
        return StoredObject(
            provider=self.provider,
            bucket=self._bucket,
            object_key=object_key,
            size_bytes=len(data),
            content_type=content_type,
            etag=(response.headers.get("etag") or "").strip('"') or None,
            last_modified=datetime.datetime.now(datetime.UTC),
        )

    async def get_object(self, *, object_key: str) -> ObjectContent | None:
        response = await self._request(
            "GET", self.full_key(object_key), allow_missing=True
        )
        if response is None:
            return None
        return ObjectContent(
            data=response.content,
            content_type=response.headers.get("content-type"),
            size_bytes=len(response.content),
            etag=(response.headers.get("etag") or "").strip('"') or None,
        )

    async def delete_object(self, *, object_key: str) -> bool:
        response = await self._request(
            "DELETE", self.full_key(object_key), allow_missing=True
        )
        return response is not None

    async def stat_object(self, *, object_key: str) -> StoredObject | None:
        response = await self._request(
            "HEAD", self.full_key(object_key), allow_missing=True
        )
        if response is None:
            return None
        modified = response.headers.get("last-modified")
        return StoredObject(
            provider=self.provider,
            bucket=self._bucket,
            object_key=object_key,
            size_bytes=int(response.headers.get("content-length") or 0),
            content_type=response.headers.get("content-type"),
            etag=(response.headers.get("etag") or "").strip('"') or None,
            last_modified=_parse_http_date(modified),
        )

    async def list_objects(self, *, prefix: str) -> AsyncIterator[StoredObject]:
        wanted = validate_prefix(prefix)
        full_prefix = f"{self._prefix}/{wanted}" if self._prefix and wanted else (
            self._prefix or wanted
        )
        continuation = ""
        while True:
            query = {
                "list-type": "2",
                "prefix": full_prefix,
                "max-keys": "1000",
            }
            if continuation:
                query["continuation-token"] = continuation
            response = await self._request("GET", "", query=query)
            assert response is not None
            root = ElementTree.fromstring(response.text)  # noqa: S314 - trusted endpoint
            for content in root.iter(f"{_NAMESPACE}Contents"):
                yield _parsed_content(content, self.provider, self._bucket, self._prefix)
            truncated = root.findtext(f"{_NAMESPACE}IsTruncated") or "false"
            if truncated.lower() != "true":
                return
            continuation = root.findtext(f"{_NAMESPACE}NextContinuationToken") or ""
            if not continuation:
                return

    async def presign_upload(
        self,
        *,
        object_key: str,
        content_type: str | None = None,
        expires_seconds: int = 900,
        max_size_bytes: int | None = None,
    ) -> PresignedUpload | None:
        del max_size_bytes  # size is enforced by the API before the upload starts
        stored = self.full_key(object_key)
        resolved_type = content_type or "application/octet-stream"
        headers = {
            "content-type": resolved_type,
            "x-amz-content-sha256": _UNSIGNED_PAYLOAD,
        }
        moment = datetime.datetime.now(datetime.UTC)
        url = presign(
            method="PUT",
            base_url=self._base_url,
            uri=self._uri_of(stored),
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
            expires_seconds=expires_seconds,
            moment=moment,
            headers=headers,
            payload_hash=_UNSIGNED_PAYLOAD,
        )
        expires_at = moment + datetime.timedelta(seconds=max(1, int(expires_seconds)))
        return PresignedUpload(
            url=url,
            expires_at=expires_at,
            object_key=object_key,
            method="PUT",
            headers=headers,
        )

    async def presign_download(
        self,
        *,
        object_key: str,
        filename: str | None = None,
        content_type: str | None = None,
        expires_seconds: int = 3600,
        inline: bool = False,
    ) -> str | None:
        stored = self.full_key(object_key)
        query: dict[str, str] = {}
        # SVG carries script: even when a caller asks to render inline it goes
        # out as an attachment.
        disposition = (
            "inline" if inline and not should_force_download(content_type) else "attachment"
        )
        if filename:
            safe = quote(filename, safe="")
            query["response-content-disposition"] = (
                f'{disposition}; filename="{filename}"; filename*=UTF-8\'\'{safe}'
            )
        if content_type:
            query["response-content-type"] = content_type
        return presign(
            method="GET",
            base_url=self._base_url,
            uri=self._uri_of(stored),
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
            expires_seconds=expires_seconds,
            moment=datetime.datetime.now(datetime.UTC),
            query=query,
            headers=None,
            payload_hash=_UNSIGNED_PAYLOAD,
        )

    async def ensure_bucket(self) -> None:
        """Create the bucket when the configuration asked for it."""
        status = await self._bucket_status()
        if status == 200:
            return
        if status != _NOT_FOUND:
            raise ServiceUnavailableError(
                f"object storage bucket is unusable: HTTP {status}"
            )
        body = _create_bucket_body(self._region)
        await self._request(
            "PUT",
            "",
            headers={"content-type": "application/xml"},
            data=body,
        )

    async def ping(self) -> None:
        status = await self._bucket_status()
        if status != 200:
            raise ServiceUnavailableError(
                f"object storage bucket is not available: HTTP {status}"
            )

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    async def _bucket_status(self) -> int:
        """Return the HTTP status of a bucket HEAD without raising."""
        try:
            response = await self._request("HEAD", "")
        except ServiceUnavailableError as failure:
            if failure.message.startswith("object storage rejected HEAD with 404"):
                return _NOT_FOUND
            raise
        return 200 if response is not None else _NOT_FOUND


def _split_endpoint(endpoint: str, *, secure: bool) -> tuple[str, str]:
    value = (endpoint or "").strip()
    if not value:
        raise ValueError("the object storage endpoint is not configured")
    scheme = "https" if secure else "http"
    if "://" in value:
        configured, _, host = value.partition("://")
        return configured.lower(), host.rstrip("/")
    return scheme, value.rstrip("/")


def _create_bucket_body(region: str) -> bytes:
    if region == "us-east-1":
        return b""
    return (
        "<CreateBucketConfiguration "
        f'xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<LocationConstraint>{region}</LocationConstraint>"
        "</CreateBucketConfiguration>"
    ).encode()


def _parse_http_date(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.UTC)


def _brief(text: str) -> str:
    """Trim an upstream error body; it is never data we own."""
    collapsed = " ".join(text.split())
    return collapsed[:180]


def _parsed_content(
    content: Any, provider: str, bucket: str, prefix: str
) -> StoredObject:
    """Translate one ``<Contents>`` element, restoring the caller's key."""
    key = content.findtext(f"{_NAMESPACE}Key") or ""
    stored_key = key[len(prefix) + 1 :] if prefix and key.startswith(f"{prefix}/") else key
    return StoredObject(
        provider=provider,
        bucket=bucket,
        object_key=stored_key,
        size_bytes=int(content.findtext(f"{_NAMESPACE}Size") or 0),
        content_type=None,
        etag=(content.findtext(f"{_NAMESPACE}ETag") or "").strip('"') or None,
        last_modified=_parse_http_date(content.findtext(f"{_NAMESPACE}LastModified")),
    )


__all__ = ["S3Storage"]
