"""Unit tests for maintenance windows.

A window must always be a positive interval: a zero length or inverted window
would suppress alert notification forever, which is worse than no window at
all. The service rejects it before anything reaches the database (the table has
a CHECK constraint as a second line of defence).

The repository is stubbed, so no database is touched.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.admin.audit.model import SysOperationLog
from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.ops.maintenance.schema import (
    MaintenanceWindowCreateRequest,
    MaintenanceWindowUpdateRequest,
)
from app.ops.maintenance.service import MaintenanceService
from app.shared.auth.context import Principal

_START = datetime.datetime(2026, 6, 1, 2, 0, tzinfo=datetime.UTC)
_END = datetime.datetime(2026, 6, 1, 4, 0, tzinfo=datetime.UTC)


class _FakeSession:
    """A session that records what the service appended and committed."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        return None

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the maintenance tests must not reach the database")

    def operations(self) -> list[str]:
        return [row.operation for row in self.added if isinstance(row, SysOperationLog)]


class _RecordingAudit:
    """Stands in for :class:`OpsAuditRecorder` and records every action."""

    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, *, action: str, **_kwargs: Any) -> None:
        self.actions.append(action)


class _StubMaintenanceRepository:
    """The window reads and writes the service touches, in memory."""

    def __init__(self, existing: SimpleNamespace | None = None) -> None:
        self._existing = existing
        self.created: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []
        self.deleted: list[int] = []

    async def get_by_code(self, window_code: str) -> SimpleNamespace | None:
        return None

    async def get(self, window_id: int) -> SimpleNamespace | None:
        return self._existing

    async def create(self, **fields: Any) -> SimpleNamespace:
        self.created.append(fields)
        return SimpleNamespace(**fields)

    async def update(self, row: SimpleNamespace, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        self.updates.append(fields)

    async def soft_delete(self, row: SimpleNamespace) -> None:
        self.deleted.append(int(row.id))


def _actor() -> Principal:
    return Principal(
        subject_id=7,
        subject_type="admin",
        session_id=1,
        username="ops-admin",
        display_name="ops admin",
    )


def _window(**overrides: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "id": 7001,
        "window_code": "WIN_NIGHTLY",
        "title": "nightly upgrade",
        "reason": None,
        "scope_type": "GLOBAL",
        "scope_id": None,
        "starts_at": _START,
        "ends_at": _END,
        "suppress_alerts": True,
        "enabled": True,
        "created_by": 7,
        "created_by_username": "ops-admin",
        "created_at": _START,
        "updated_at": _START,
        "deleted_at": None,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _service(
    existing: SimpleNamespace | None = None,
) -> tuple[MaintenanceService, _StubMaintenanceRepository, _FakeSession, _RecordingAudit]:
    session = _FakeSession()
    service = MaintenanceService(session, Settings(_env_file=None))
    repository = _StubMaintenanceRepository(existing)
    audit = _RecordingAudit()
    service._repository = repository  # type: ignore[attr-defined]
    service._audit = audit  # type: ignore[attr-defined]
    return service, repository, session, audit


def _create(**overrides: Any) -> MaintenanceWindowCreateRequest:
    fields: dict[str, Any] = {
        "window_code": "WIN_NIGHTLY",
        "title": "nightly upgrade",
        "starts_at": _START,
        "ends_at": _END,
    }
    fields.update(overrides)
    return MaintenanceWindowCreateRequest(**fields)  # type: ignore[arg-type]


@pytest.mark.asyncio()
async def test_a_window_that_ends_when_it_starts_is_refused() -> None:
    service, repository, session, audit = _service()

    with pytest.raises(ValidationError):
        await service.create_window(_actor(), _create(ends_at=_START))

    assert repository.created == []
    assert audit.actions == []
    assert session.commits == 0


@pytest.mark.asyncio()
async def test_an_inverted_window_is_refused() -> None:
    service, repository, _session, audit = _service()

    with pytest.raises(ValidationError):
        await service.create_window(
            _actor(), _create(ends_at=_START - datetime.timedelta(hours=1))
        )

    assert repository.created == []
    assert audit.actions == []


@pytest.mark.asyncio()
async def test_a_positive_window_is_created_and_audited() -> None:
    service, repository, session, audit = _service()

    response = await service.create_window(_actor(), _create())

    assert response.window_code == "WIN_NIGHTLY"
    assert response.starts_at == _START
    assert response.ends_at == _END
    assert repository.created[0]["ends_at"] > repository.created[0]["starts_at"]
    assert audit.actions == ["OPS_MAINTENANCE_CREATE"]
    assert session.operations() == ["OPS_MAINTENANCE_CREATE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_update_that_would_invert_the_interval_is_refused() -> None:
    """Only one end is sent; the other end comes from the stored window."""
    existing = _window()
    service, repository, session, audit = _service(existing)

    with pytest.raises(ValidationError):
        await service.update_window(
            _actor(),
            7001,
            MaintenanceWindowUpdateRequest(ends_at=_START - datetime.timedelta(minutes=1)),
        )

    assert repository.updates == []
    assert audit.actions == []
    assert session.commits == 0


@pytest.mark.asyncio()
async def test_update_that_would_move_the_start_past_the_end_is_refused() -> None:
    existing = _window()
    service, repository, _session, _audit = _service(existing)

    with pytest.raises(ValidationError):
        await service.update_window(
            _actor(), 7001, MaintenanceWindowUpdateRequest(starts_at=_END)
        )

    assert repository.updates == []


@pytest.mark.asyncio()
async def test_update_accepts_a_still_positive_interval() -> None:
    existing = _window()
    service, repository, session, audit = _service(existing)
    later_end = _END + datetime.timedelta(hours=1)

    response = await service.update_window(
        _actor(), 7001, MaintenanceWindowUpdateRequest(ends_at=later_end)
    )

    assert response.ends_at == later_end
    assert repository.updates == [{"ends_at": later_end}]
    assert audit.actions == ["OPS_MAINTENANCE_UPDATE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_delete_soft_deletes_and_audits() -> None:
    existing = _window()
    service, repository, session, audit = _service(existing)

    await service.delete_window(_actor(), 7001)

    assert repository.deleted == [7001]
    assert audit.actions == ["OPS_MAINTENANCE_DELETE"]
    assert session.commits == 1


@pytest.mark.asyncio()
async def test_an_active_window_suppresses_alert_notification() -> None:
    """维护窗口生效期内应抑制告警通知。"""
    now = datetime.datetime.now(datetime.UTC)
    window = _window(
        starts_at=now - datetime.timedelta(hours=1),
        ends_at=now + datetime.timedelta(hours=1),
        suppress_alerts=True,
        enabled=True,
    )
    service, _repository, _session, _audit = _service(window)

    assert await service.suppresses_notifications(window, at=now) is True


@pytest.mark.asyncio()
async def test_a_window_outside_its_interval_does_not_suppress() -> None:
    """未开始、已结束、被停用或本就不抑制的窗口都不生效。"""
    now = datetime.datetime.now(datetime.UTC)
    active = _window(
        starts_at=now - datetime.timedelta(hours=1),
        ends_at=now + datetime.timedelta(hours=1),
    )
    service, _repository, _session, _audit = _service(active)
    future = _window(starts_at=now + datetime.timedelta(hours=1))
    past = _window(
        starts_at=now - datetime.timedelta(hours=2),
        ends_at=now - datetime.timedelta(hours=1),
    )

    assert await service.suppresses_notifications(future, at=now) is False
    assert await service.suppresses_notifications(past, at=now) is False
    assert await service.suppresses_notifications(active, at=now) is True
    # 关闭抑制开关或停用窗口后，窗口依然存在但不再静音。
    assert (
        await service.suppresses_notifications(
            _window(suppress_alerts=False), at=now - datetime.timedelta(minutes=1)
        )
        is False
    )
    assert (
        await service.suppresses_notifications(
            _window(enabled=False), at=now - datetime.timedelta(minutes=1)
        )
        is False
    )
    # 区间端点闭合：结束那一刻仍在维护中。
    assert (
        await service.suppresses_notifications(
            _window(starts_at=now, ends_at=now + datetime.timedelta(hours=1)), at=now
        )
        is True
    )
