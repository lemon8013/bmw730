"""Idempotency service.

Repeating a request must never repeat its side effect: a second registration,
reward, point deduction, task completion or batch export with the same key
returns the first response instead of applying the change twice.

The guard is the database ``UNIQUE(scope, idempotency_key)`` constraint, so the
protection also holds under real concurrency - two simultaneous requests cannot
both win the insert. The insert happens inside a savepoint so that a losing
race leaves the caller's transaction usable instead of aborting it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import IdempotencyError
from app.shared.ids import new_id
from app.system.jobs.model import SysIdempotencyRecord

STATUS_PROCESSING: Final[str] = "PROCESSING"
STATUS_COMPLETED: Final[str] = "COMPLETED"
STATUS_FAILED: Final[str] = "FAILED"


def build_request_hash(payload: Any) -> str:
    """Return a stable digest of a request payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IdempotencyState:
    """Outcome of an idempotency claim."""

    record_id: int
    is_new: bool
    status: str
    request_hash: str
    response_code: int | None
    response_body: dict[str, Any] | None

    @property
    def replayable(self) -> bool:
        """Whether a stored response can be returned instead of re-running."""
        return self.status == STATUS_COMPLETED and self.response_body is not None


class IdempotencyService:
    """Guards repeated requests through ``sys_idempotency_record``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _expiry(self, now: datetime) -> datetime:
        return now + timedelta(seconds=self._settings.IDEMPOTENCY_TTL_SECONDS)

    async def _load(
        self, session: AsyncSession, *, key: str, scope: str
    ) -> SysIdempotencyRecord | None:
        result = await session.execute(
            select(SysIdempotencyRecord).where(
                SysIdempotencyRecord.scope == scope,
                SysIdempotencyRecord.idempotency_key == key,
            )
        )
        return result.scalar_one_or_none()

    def _state_from(self, record: SysIdempotencyRecord, *, is_new: bool) -> IdempotencyState:
        return IdempotencyState(
            record_id=record.id,
            is_new=is_new,
            status=record.status,
            request_hash=record.request_hash,
            response_code=record.response_code,
            response_body=record.response_body,
        )

    async def start(
        self,
        session: AsyncSession,
        *,
        key: str,
        scope: str,
        request_hash: str,
        now: datetime | None = None,
    ) -> IdempotencyState:
        """Claim an idempotency key.

        Returns a state whose ``replayable`` flag tells the caller to return the
        stored response instead of performing the operation again.

        Raises:
            IdempotencyError: when the key is already in flight, or was already
                used with a different payload.
        """
        reference = now or datetime.now(tz=UTC)

        existing = await self._load(session, key=key, scope=scope)
        if existing is None:
            record = SysIdempotencyRecord(
                id=new_id(),
                idempotency_key=key,
                scope=scope,
                request_hash=request_hash,
                status=STATUS_PROCESSING,
                expires_at=self._expiry(reference),
            )
            try:
                async with session.begin_nested():
                    session.add(record)
                    await session.flush()
            except IntegrityError:
                winner = await self._load(session, key=key, scope=scope)
                if winner is None:  # pragma: no cover - the row must exist
                    raise IdempotencyError(
                        "an identical request is already being processed"
                    ) from None
                existing = winner
            else:
                return self._state_from(record, is_new=True)

        if existing is None:  # pragma: no cover - unreachable, keeps mypy precise
            raise IdempotencyError("an identical request is already being processed")

        if existing.request_hash != request_hash:
            raise IdempotencyError("the idempotency key was already used with a different payload")
        if existing.status == STATUS_PROCESSING:
            raise IdempotencyError("an identical request is already being processed")
        if existing.expires_at is not None and existing.expires_at < reference:
            existing.status = STATUS_PROCESSING
            existing.response_code = None
            existing.response_body = None
            existing.expires_at = self._expiry(reference)
            await session.flush()
            return self._state_from(existing, is_new=True)

        return self._state_from(existing, is_new=False)

    async def complete(
        self,
        session: AsyncSession,
        *,
        record_id: int,
        response_code: int,
        response_body: dict[str, Any] | None,
        now: datetime | None = None,
    ) -> None:
        """Store the response so a replay can return it verbatim."""
        reference = now or datetime.now(tz=UTC)
        record = await session.get(SysIdempotencyRecord, record_id)
        if record is None:  # pragma: no cover - the row was claimed in this transaction
            return
        record.status = STATUS_COMPLETED
        record.response_code = response_code
        record.response_body = response_body
        record.updated_at = reference
        await session.flush()

    async def fail(self, session: AsyncSession, *, record_id: int) -> None:
        """Mark a failed attempt so the same key may be retried."""
        record = await session.get(SysIdempotencyRecord, record_id)
        if record is None:  # pragma: no cover
            return
        record.status = STATUS_FAILED
        record.response_code = None
        record.response_body = None
        await session.flush()

    async def purge_expired(self, session: AsyncSession, *, now: datetime | None = None) -> int:
        """Delete idempotency records whose TTL elapsed."""
        reference = now or datetime.now(tz=UTC)
        result = await session.execute(
            delete(SysIdempotencyRecord).where(SysIdempotencyRecord.expires_at < reference)
        )
        return int(result.rowcount or 0)
