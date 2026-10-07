"""app.ops.events — ORM models.

An event is a state change of the system. It is deliberately **not** an alert:
an alert is a human facing consequence derived from rules, while an event is the
raw fact that something changed.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsEvent(Base):
    """ops_event — a system state change."""

    __tablename__ = "ops_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    event_id: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="事件业务 ID")
    event_type: Mapped[str] = mapped_column(
        sa.String(64), nullable=False,
        comment="事件类型（SERVICE_DOWN/HOST_OFFLINE/AGENT_OFFLINE/JOB_FAILED/JOB_TIMEOUT/...）",
    )
    source: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="事件来源")
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="资源类型"
    )
    resource_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="资源 ID")
    severity: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'INFO'"),
        comment="严重级别（INFO/WARNING/ERROR/CRITICAL）",
    )
    message: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True, comment="事件描述")
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="链路追踪 ID"
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="请求 ID")
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="事件发生时间（UTC）"
    )
    metadata_payload: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="结构化扩展属性",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint("event_id", name="uq_ops_event_id"),
        sa.Index("ix_ops_event_type_occurred", "event_type", "occurred_at"),
        sa.Index("ix_ops_event_occurred", "occurred_at"),
        sa.Index("ix_ops_event_trace", "trace_id"),
        {"comment": "运维事件"},
    )
