"""app.ops.availability — ORM models.

Availability probes: HTTP, TCP, DNS and SSL certificate expiry. Providers are
registered per probe type, so a new probe adds a provider instead of a branch.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsAvailabilityCheck(Base):
    """ops_availability_check — a probe definition."""

    __tablename__ = "ops_availability_check"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    check_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="检查编码")
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="检查名称")
    check_type: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, comment="检查类型（HTTP/TCP/DNS/SSL）"
    )
    target: Mapped[str] = mapped_column(sa.String(500), nullable=False, comment="检查目标")
    service_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_service.id"), nullable=True, comment="关联服务"
    )
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    timeout_ms: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("5000"), comment="超时毫秒"
    )
    interval_seconds: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("60"), comment="检查间隔秒"
    )
    expected_status: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True, comment="HTTP 期望状态码"
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
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
        sa.UniqueConstraint("check_code", name="uq_ops_availability_check_code"),
        sa.Index("ix_ops_availability_check_type", "check_type"),
        {"comment": "运维可用性检查"},
    )


class OpsAvailabilityResult(Base):
    """ops_availability_result — one probe execution result."""

    __tablename__ = "ops_availability_result"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    check_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("ops_availability_check.id"),
        nullable=False,
        comment="所属检查",
    )
    success: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, comment="是否成功")
    latency_ms: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="延迟毫秒")
    status_code: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True, comment="HTTP 状态码"
    )
    error_message: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True,
        comment="错误信息")
    detail: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="检查结果明细（SSL 颁发者/有效期等）",
    )
    checked_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="检查时间（UTC）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_availability_result_check_time", "check_id", "checked_at"),
        {"comment": "运维可用性检查结果"},
    )
