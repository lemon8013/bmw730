"""Prove that the configured object storage really works.

Run it right after filling in the credentials of the object store (RustFS, MinIO,
Ceph RGW, AWS S3), and again after every credential rotation:

    python -m app.scripts.storage_check

It verifies the only things that matter before go-live: the bucket exists (or is
created), an object can be written, read back byte for byte, described, given a
temporary URL and deleted again. A failure here means every upload in the
application will fail, so it is worth knowing before a user finds out.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from app.core.config import Settings, get_settings
from app.shared.storage import get_object_storage
from app.shared.storage.keys import build_object_key

_PROBE_BODY = b"vctn storage check\n" + b"\x00" * 32


async def _run(settings: Settings, *, keep: bool) -> int:
    storage = get_object_storage(settings)
    started = time.perf_counter()
    print(f"provider : {storage.provider}")
    print(f"bucket   : {getattr(storage, 'bucket', '?')}")
    if settings.S3_ENDPOINT:
        # Deliberately not printing the endpoint with credentials: the endpoint
        # alone tells an operator which environment they are pointing at.
        print(f"endpoint : {settings.S3_ENDPOINT}")

    await storage.ensure_bucket()
    await storage.ping()
    print("bucket   : reachable")

    key = build_object_key(category="storage-check", original_name="probe.txt")
    stored = await storage.put_object(
        object_key=key, data=_PROBE_BODY, content_type="text/plain"
    )
    print(f"put      : {key} ({stored.size_bytes} bytes)")

    content = await storage.get_object(object_key=key)
    if content is None or content.data != _PROBE_BODY:
        print("get      : FAILED - the object was not read back correctly")
        return 1
    print("get      : byte for byte identical")

    head = await storage.stat_object(object_key=key)
    print(f"head     : {head.size_bytes if head else 0} bytes")

    upload = await storage.presign_upload(
        object_key=key,
        content_type="text/plain",
        expires_seconds=settings.FILE_PRESIGN_TTL_SECONDS,
    )
    if upload is None:
        print("presign  : unsupported by this backend (uploads go through the API)")
    else:
        print(f"presign  : PUT url valid until {upload.expires_at.isoformat()}")

    download = await storage.presign_download(
        object_key=key, filename="probe.txt", content_type="text/plain", expires_seconds=60
    )
    if download is None:
        print("download : served through the API (no pre-signed URL)")
    else:
        print("download : pre-signed URL issued")

    if not keep:
        await storage.delete_object(object_key=key)
        print("delete   : removed")

    elapsed = time.perf_counter() - started
    print(f"ok in {elapsed:.2f}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m app.scripts.storage_check",
        description="Write, read and delete a probe object in the configured storage.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="leave the probe object behind (for inspecting it in the console)",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    try:
        return asyncio.run(_run(settings, keep=args.keep))
    except Exception as failure:  # noqa: BLE001 - the CLI reports, it never traces
        print(f"FAILED: {type(failure).__name__}: {failure}", file=sys.stderr)
        print(
            "Check FILE_STORAGE_PROVIDER and, for an object store, S3_ENDPOINT / "
            "S3_BUCKET / S3_ACCESS_KEY / S3_SECRET_KEY.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
