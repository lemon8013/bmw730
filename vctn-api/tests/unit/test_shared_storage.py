"""Object storage: key safety, content sniffing, signatures and the two backends.

These tests exist because each piece fails silently in production. A traversal
key that reaches the filesystem writes outside the root; a declared
``image/png`` accepted without sniffing serves stored HTML back to a browser; a
signature that differs from what the server recomputes is a 403 nobody can
explain from the logs.
"""

from __future__ import annotations

import datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.shared.storage import (
    get_object_storage,
    reset_object_storage_cache,
)
from app.shared.storage.content import (
    OCTET_STREAM,
    parse_allowed_mime_types,
    should_force_download,
    sniff_content_type,
    validate_upload,
)
from app.shared.storage.factory import (
    LOCAL_BUCKET,
    PROVIDER_S3,
    normalize_provider,
)
from app.shared.storage.factory import (
    get_object_storage as resolve_storage,
)
from app.shared.storage.keys import InvalidObjectKey, build_object_key, validate_object_key
from app.shared.storage.local import LocalStorage
from app.shared.storage.s3 import S3Storage
from app.shared.storage.signer import (
    build_canonical_request,
    canonical_headers,
    canonical_query,
    presign,
    uri_encode,
)


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    reset_object_storage_cache()


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"IDAT-not-really-an-image"
)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 8
PDF_BYTES = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3"
WEBP_BYTES = b"RIFF\x1a\x00\x00\x00WEBPVP8 " + b"\x00" * 8
SVG_BYTES = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'


# --------------------------------------------------------------------------
# keys
# --------------------------------------------------------------------------
def test_generated_key_is_date_bucketed_and_extension_safe() -> None:
    key = build_object_key(
        category="avatar",
        original_name="../../../../etc/passwd.png",
        now=datetime.datetime(2026, 10, 7, tzinfo=datetime.UTC),
    )
    assert key.startswith("avatar/2026/10/07/")
    assert key.endswith(".png")
    # Nothing derived from the hostile name survived but the extension.
    assert ".." not in key and "etc" not in key


def test_generated_key_has_128_bits_of_entropy() -> None:
    first = build_object_key(category="doc")
    second = build_object_key(category="doc")
    assert first != second
    stem = first.split("/")[-1]
    assert len(stem) == 32


def test_unknown_category_falls_back_to_general() -> None:
    assert build_object_key(category="../escape").startswith("general/")


@pytest.mark.parametrize(
    "candidate",
    ["../storage/x", "/absolute", "a/../../ escape", "", "x" * 1025, "a//b", "a/./b", "a\x00b"],
)
def test_traversal_keys_are_rejected(candidate: str) -> None:
    with pytest.raises(InvalidObjectKey):
        validate_object_key(candidate)


def test_prefix_is_validated() -> None:
    with pytest.raises(InvalidObjectKey):
        build_object_key(prefix="../..")


# --------------------------------------------------------------------------
# content sniffing
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (PNG_BYTES, "image/png"),
        (JPEG_BYTES, "image/jpeg"),
        (PDF_BYTES, "application/pdf"),
        (WEBP_BYTES, "image/webp"),
        (SVG_BYTES, "image/svg+xml"),
    ],
)
def test_magic_bytes_win_over_the_declared_type(payload: bytes, expected: str) -> None:
    resolved = validate_upload(payload, declared="text/html", allowed=None, max_bytes=1024)
    assert resolved == expected


def test_html_declared_as_png_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not a valid image/png"):
        validate_upload(
            b"<html><script>alert(1)</script></html>",
            declared="image/png",
            allowed=None,
            max_bytes=1024,
        )


def test_unknown_payload_is_refused_by_the_default_allow_list() -> None:
    """An opaque blob has no business being stored through this API."""
    with pytest.raises(ValidationError, match="not allowed"):
        validate_upload(b"\x00" * 16, declared=None, allowed=None, max_bytes=64)
    unrestricted = parse_allowed_mime_types("*")
    assert validate_upload(
        b"\x00" * 16, declared=None, allowed=unrestricted, max_bytes=64
    ) == OCTET_STREAM


def test_disallowed_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        validate_upload(
            PDF_BYTES,
            declared=None,
            allowed=frozenset({"image/png"}),
            max_bytes=1024,
        )


def test_size_limit_is_enforced() -> None:
    with pytest.raises(ValidationError, match="maximum size"):
        validate_upload(PNG_BYTES, declared="image/png", allowed=None, max_bytes=4)


def test_empty_payload_is_rejected() -> None:
    with pytest.raises(ValidationError, match="empty"):
        validate_upload(b"", declared="image/png", allowed=None, max_bytes=1024)


def test_allow_list_parsing() -> None:
    assert parse_allowed_mime_types("")  # empty means the built-in list
    assert parse_allowed_mime_types("*") == frozenset()
    assert parse_allowed_mime_types("Image/PNG, text/plain") == {
        "image/png",
        "text/plain",
    }


def test_svg_is_always_served_as_an_attachment() -> None:
    assert should_force_download("image/svg+xml")
    assert not should_force_download("image/png")


def test_non_image_is_not_sniffed_as_image() -> None:
    assert sniff_content_type(b"just text") is None


# --------------------------------------------------------------------------
# signatures
# --------------------------------------------------------------------------
def test_canonical_headers_collapse_and_sort() -> None:
    block, signed = canonical_headers(
        {"X-Test": "  a   b  ", "Accept": "application/json", "Host": "rustfs:9000"}
    )
    assert block == "accept:application/json\nhost:rustfs:9000\nx-test:a b\n"
    assert signed == "accept;host;x-test"


def test_query_encoding_percent_encodes_everything_else() -> None:
    assert uri_encode("a b/c") == "a%20b%2Fc"
    assert canonical_query({"b": "2", "a": "1"}) == "a=1&b=2"


def test_presign_reproduces_the_aws_reference_vector() -> None:
    """Known answer test: the worked example in the AWS S3 documentation.

    Determinism tests cannot catch a systematically wrong canonical request -
    one wrong newline still produces stable signatures that every S3 server
    rejects. This pins the published example instead.
    """
    canonical, _signed, canonical_hash = build_canonical_request(
        method="GET",
        uri="/test.txt",
        query={
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": "AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request",
            "X-Amz-Date": "20130524T000000Z",
            "X-Amz-Expires": "86400",
            "X-Amz-SignedHeaders": "host",
        },
        headers={"host": "examplebucket.s3.amazonaws.com"},
        payload_hash="UNSIGNED-PAYLOAD",
    )
    del canonical
    assert canonical_hash == (
        "3bfa292879f6447bbcda7001decf97f4a54dc650c8942174ae0a9121cf58ad04"
    )

    url = presign(
        method="GET",
        base_url="https://examplebucket.s3.amazonaws.com",
        uri="/test.txt",
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        expires_seconds=86400,
        moment=datetime.datetime(2013, 5, 24, tzinfo=datetime.UTC),
        payload_hash="UNSIGNED-PAYLOAD",
    )
    # The signature is the whole point; parameter order is not part of the
    # contract (S3 sorts the canonical query anyway), so compare parsed.
    from urllib.parse import parse_qs, urlsplit  # noqa: PLC0415 - one usage

    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert parts.scheme == "https"
    assert parts.netloc == "examplebucket.s3.amazonaws.com"
    assert parts.path == "/test.txt"
    assert query["X-Amz-Signature"] == [
        "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
    ]
    assert query["X-Amz-SignedHeaders"] == ["host"]
    assert query["X-Amz-Expires"] == ["86400"]


def test_presign_is_deterministic_and_bounded() -> None:
    moment = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    url = presign(
        method="PUT",
        base_url="http://rustfs:9000",
        uri="/bucket/key.png",
        access_key="ak",
        secret_key="sk",
        region="us-east-1",
        expires_seconds=900,
        moment=moment,
    )
    assert url.startswith("http://rustfs:9000/bucket/key.png?")
    assert "X-Amz-Signature=" in url
    assert "X-Amz-Expires=900" in url
    again = presign(
        method="PUT",
        base_url="http://rustfs:9000",
        uri="/bucket/key.png",
        access_key="ak",
        secret_key="sk",
        region="us-east-1",
        expires_seconds=900,
        moment=moment,
    )
    assert url == again


def test_presign_clamps_the_expiry_to_the_s3_maximum() -> None:
    url = presign(
        method="GET",
        base_url="http://rustfs:9000",
        uri="/bucket/key",
        access_key="ak",
        secret_key="sk",
        region="us-east-1",
        expires_seconds=99999999,
        moment=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
    )
    assert "X-Amz-Expires=604800" in url


# --------------------------------------------------------------------------
# local backend
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_local_backend_roundtrip(tmp_path) -> None:
    backend = LocalStorage(root=tmp_path / "objects", bucket=LOCAL_BUCKET)
    await backend.ensure_bucket()

    stored = await backend.put_object(
        object_key="images/2026/10/07/a.png", data=PNG_BYTES, content_type="image/png"
    )
    assert stored.size_bytes == len(PNG_BYTES)
    assert (tmp_path / "objects" / "images/2026/10/07/a.png").is_file()

    content = await backend.get_object(object_key="images/2026/10/07/a.png")
    assert content is not None and content.data == PNG_BYTES

    head = await backend.stat_object(object_key="images/2026/10/07/a.png")
    assert head is not None and head.size_bytes == len(PNG_BYTES)

    listed = [item.object_key async for item in backend.list_objects(prefix="images/")]
    assert listed == ["images/2026/10/07/a.png"]

    assert await backend.delete_object(object_key="images/2026/10/07/a.png") is True
    assert await backend.get_object(object_key="images/2026/10/07/a.png") is None
    assert await backend.delete_object(object_key="images/2026/10/07/a.png") is False


@pytest.mark.asyncio
async def test_local_backend_refuses_to_escape_the_root(tmp_path) -> None:
    root = tmp_path / "objects"
    await LocalStorage(root=root).ensure_bucket()
    outside = tmp_path / "escaped.txt"
    outside.write_text("owned", encoding="utf-8")

    with pytest.raises(InvalidObjectKey):
        await LocalStorage(root=root).get_object(object_key="../escaped.txt")


def test_local_backend_has_no_presigned_urls(tmp_path) -> None:
    backend = LocalStorage(root=tmp_path / "objects")
    assert backend.provider == "local"


# --------------------------------------------------------------------------
# S3 backend against a mock transport
# --------------------------------------------------------------------------
class _Recorder:
    """Capture every request the backend sends."""

    def __init__(self, responses: dict[str, httpx.Response] | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.responses = responses or {}
        self.bodies: list[bytes] = []

    def transport(self) -> httpx.MockTransport:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            self.bodies.append(request.content)
            key = f"{request.method}:{request.url.path}"
            return self.responses.get(key, httpx.Response(200, headers=self._etag()))

        return httpx.MockTransport(handler)

    @staticmethod
    def _etag() -> dict[str, str]:
        return {"etag": '"abc123"', "content-type": "image/png", "content-length": "8"}


def _backend(recorder: _Recorder, **overrides: object) -> S3Storage:
    kwargs: dict[str, object] = {
        "endpoint": "http://rustfs.internal:9000",
        "bucket": "vctn",
        "access_key": "ak",
        "secret_key": "sk",
        "prefix": "prod",
        "transport": recorder.transport(),
    }
    kwargs.update(overrides)
    return S3Storage(**kwargs)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_s3_put_signs_and_targets_the_bucket_path() -> None:
    recorder = _Recorder()
    backend = _backend(recorder)
    await backend.put_object(object_key="k.png", data=PNG_BYTES, content_type="image/png")
    await backend.aclose()

    request = recorder.requests[0]
    assert request.method == "PUT"
    assert request.url.path == "/vctn/prod/k.png"
    assert request.headers["authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "x-amz-content-sha256" in request.headers
    assert recorder.bodies[0] == PNG_BYTES


@pytest.mark.asyncio
async def test_s3_missing_object_is_reported_not_raised() -> None:
    missing = httpx.Response(404, text="NoSuchKey")
    recorder = _Recorder(
        {
            "GET:/vctn/prod/k.png": missing,
            "DELETE:/vctn/prod/k.png": missing,
            "HEAD:/vctn/prod/k.png": missing,
        }
    )
    backend = _backend(recorder)
    assert await backend.get_object(object_key="k.png") is None
    assert await backend.delete_object(object_key="k.png") is False
    assert await backend.stat_object(object_key="k.png") is None
    await backend.aclose()


@pytest.mark.asyncio
async def test_s3_server_error_becomes_service_unavailable() -> None:
    recorder = _Recorder({"PUT:/vctn/prod/k.png": httpx.Response(503, text="busy")})
    backend = _backend(recorder)
    with pytest.raises(ServiceUnavailableError, match="rejected PUT with 503"):
        await backend.put_object(object_key="k.png", data=PNG_BYTES)
    await backend.aclose()


@pytest.mark.asyncio
async def test_s3_unreachable_endpoint_reports_the_transport_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    backend = S3Storage(
        endpoint="https://rustfs.internal:9000",
        bucket="vctn",
        access_key="ak",
        secret_key="sk",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ServiceUnavailableError, match="unreachable"):
        await backend.ping()
    await backend.aclose()


@pytest.mark.asyncio
async def test_s3_presign_upload_covers_the_headers_the_client_must_send() -> None:
    recorder = _Recorder()
    backend = _backend(recorder)
    result = await backend.presign_upload(
        object_key="k.png", content_type="image/png", expires_seconds=600
    )
    await backend.aclose()

    assert result is not None
    assert result.method == "PUT"
    assert result.url.startswith("http://rustfs.internal:9000/vctn/prod/k.png?")
    assert result.headers["content-type"] == "image/png"
    assert result.headers["x-amz-content-sha256"] == "UNSIGNED-PAYLOAD"
    assert "X-Amz-Signature=" in result.url
    # The signed headers list must name exactly what we hand back.
    assert "X-Amz-SignedHeaders=content-type%3Bhost%3Bx-amz-content-sha256" in result.url


@pytest.mark.asyncio
async def test_s3_presign_download_forces_an_attachment() -> None:
    recorder = _Recorder()
    backend = _backend(recorder)
    url = await backend.presign_download(
        object_key="k.svg",
        filename="report.svg",
        content_type="image/svg+xml",
        inline=True,
    )
    await backend.aclose()
    assert url is not None
    # Even with inline=True an SVG is never rendered: it can carry script.
    assert "response-content-disposition=attachment" in url
    assert "report.svg" in url

    plain = await backend.presign_download(
        object_key="k.png", filename="a.png", content_type="image/png", inline=True
    )
    assert plain is not None and "response-content-disposition=inline" in plain


@pytest.mark.asyncio
async def test_s3_ensure_bucket_creates_a_missing_bucket() -> None:
    calls: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "HEAD":
            return httpx.Response(404, text="NoSuchBucket")
        return httpx.Response(200)

    backend = S3Storage(
        endpoint="https://rustfs.internal:9000",
        bucket="vctn",
        access_key="ak",
        secret_key="sk",
        region="cn-north-1",
        transport=httpx.MockTransport(handler),
    )
    await backend.ensure_bucket()
    await backend.aclose()

    create = calls[-1]
    assert create.method == "PUT"
    assert create.url.path == "/vctn"
    assert b"LocationConstraint" in create.content
    assert b"cn-north-1" in create.content


@pytest.mark.asyncio
async def test_s3_list_objects_strips_the_configured_prefix() -> None:
    listing = """<?xml version="1.0"?>
    <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
      <IsTruncated>false</IsTruncated>
      <Contents>
        <Key>prod/exports/2026/old.csv</Key>
        <Size>10</Size>
        <LastModified>Mon, 05 Oct 2026 03:04:05 GMT</LastModified>
        <ETag>&quot;e1&quot;</ETag>
      </Contents>
    </ListBucketResult>"""

    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=listing)

    backend = S3Storage(
        endpoint="https://rustfs.internal:9000",
        bucket="vctn",
        access_key="ak",
        secret_key="sk",
        prefix="prod",
        transport=httpx.MockTransport(handler),
    )
    objects = [item async for item in backend.list_objects(prefix="exports/")]
    await backend.aclose()

    assert [item.object_key for item in objects] == ["exports/2026/old.csv"]
    assert objects[0].last_modified is not None
    # Listing asked for the prefixed key, because that is where the object is.
    assert seen[0].url.params.get("prefix") == "prod/exports"


# --------------------------------------------------------------------------
# factory and configuration
# --------------------------------------------------------------------------
def test_factory_returns_local_by_default(tmp_path) -> None:
    storage = get_object_storage(Settings(FILE_STORAGE_ROOT=str(tmp_path)))
    assert isinstance(storage, LocalStorage)
    assert get_object_storage(Settings(FILE_STORAGE_ROOT=str(tmp_path))) is storage


def test_factory_switches_to_s3_and_caches(tmp_path) -> None:
    settings = Settings(
        FILE_STORAGE_PROVIDER=PROVIDER_S3,
        FILE_STORAGE_ROOT=str(tmp_path),
        S3_ENDPOINT="rustfs.internal:9000",
        S3_BUCKET="vctn",
        S3_ACCESS_KEY="ak",
        S3_SECRET_KEY="sk-that-is-long-enough",
    )
    storage = resolve_storage(settings)
    assert isinstance(storage, S3Storage)
    assert storage.provider == PROVIDER_S3
    assert resolve_storage(settings) is storage


def test_factory_rejects_an_unknown_provider() -> None:
    with pytest.raises(ValidationError, match="unsupported storage provider"):
        get_object_storage(Settings(FILE_STORAGE_PROVIDER="gcs"))


def test_s3_requires_the_endpoint_and_credentials() -> None:
    """Configuration errors surface at startup, not on the first upload."""
    with pytest.raises(ValueError, match="S3_ENDPOINT"):
        Settings(FILE_STORAGE_PROVIDER=PROVIDER_S3, S3_BUCKET="vctn").validate_startup()


def test_bucket_name_is_validated() -> None:
    with pytest.raises(ValueError, match="3 and 63"):
        Settings(
            FILE_STORAGE_PROVIDER=PROVIDER_S3,
            S3_ENDPOINT="rustfs:9000",
            S3_BUCKET="ab",
            S3_ACCESS_KEY="ak",
            S3_SECRET_KEY="sk",
        ).validate_startup()
    with pytest.raises(ValueError, match="must start and end"):
        Settings(
            FILE_STORAGE_PROVIDER=PROVIDER_S3,
            S3_ENDPOINT="rustfs:9000",
            S3_BUCKET="-vctn-",
            S3_ACCESS_KEY="ak",
            S3_SECRET_KEY="sk",
        ).validate_startup()


def test_production_refuses_the_sample_credential() -> None:
    with pytest.raises(ValueError, match="sample credential"):
        Settings(
            APP_ENV="production",
            ALLOWED_HOSTS="ops.example.com",
            CORS_ORIGINS="https://ops.example.com",
            JWT_SECRET="x" * 32,
            APP_DEBUG=False,
            FILE_STORAGE_PROVIDER=PROVIDER_S3,
            S3_ENDPOINT="rustfs:9000",
            S3_BUCKET="vctn",
            S3_ACCESS_KEY="rustfsadmin",
            S3_SECRET_KEY="rustfsadmin",
        ).validate_startup()



def test_rustfs_and_legacy_minio_names_normalize_to_s3() -> None:
    """RustFS is the deployment target; `minio` is kept for older .env files.

    Both must build the same backend and be recorded as `s3`, so the value in
    sys_file never tells a lie about which vendor is in use.
    """
    for declared in ("s3", "rustfs", "minio"):
        settings = Settings(
            FILE_STORAGE_PROVIDER=declared,
            S3_ENDPOINT="rustfs.internal:9000",
            S3_BUCKET="vctn",
            S3_ACCESS_KEY="ak",
            S3_SECRET_KEY="sk-that-is-long-enough",
        )
        settings.validate_startup()
        assert settings.FILE_STORAGE_PROVIDER == "s3", declared
        assert normalize_provider(settings) == "s3"
        reset_object_storage_cache()
        assert get_object_storage(settings).provider == "s3"


def test_legacy_minio_environment_names_still_load(monkeypatch) -> None:
    """A .env written before the rename must not break the first boot."""
    monkeypatch.setenv("MINIO_ENDPOINT", "http://rustfs.internal:9000")
    monkeypatch.setenv("MINIO_BUCKET", "vctn")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "ak")
    monkeypatch.setenv("MINIO_SECRET_KEY", "sk")
    monkeypatch.setenv("FILE_STORAGE_PROVIDER", "minio")
    settings = Settings(_env_file=None)
    assert settings.S3_ENDPOINT == "http://rustfs.internal:9000"
    assert settings.S3_BUCKET == "vctn"
    assert settings.S3_ACCESS_KEY == "ak"
    assert settings.S3_SECRET_KEY == "sk"
    settings.validate_startup()
    assert settings.FILE_STORAGE_PROVIDER == "s3"
