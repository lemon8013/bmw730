"""app.ops.maintenance — ORM models.

A maintenance window suppresses alert **notification** for its scope. It never
rewrites metrics or events: the raw facts stay intact so the timeline can always
be reconstructed afterwards.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsMaintenanceWindow(Base):
    """ops_maintenance_window — a planned suppression window."""

    __tablename__ = "ops_maintenance_window"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    window_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="维护窗口编码")
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False, comment="标题")
    reason: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True, comment="维护原因")
    scope_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'GLOBAL'"),
        comment="作用范围类型（GLOBAL/HOST/SERVICE/ENDPOINT）",
    )
    scope_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="作用范围对象 ID"
    )
    starts_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="开始时间（UTC）"
    )
    ends_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="结束时间（UTC）"
    )
    suppress_alerts: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否抑制告警通知"
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="创建人")
    created_by_username: Mapped[str | None] = mapped_column(sa.String(64), nullable=True,
        comment="创建人账号")
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="更新时间（UTC）"
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint("window_code", name="uq_ops_maintenance_window_code"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_ops_maintenance_window_range"),
        sa.Index("ix_ops_maintenance_window_range", "starts_at", "ends_at"),
        {"comment": "运维维护窗口"},
    )
