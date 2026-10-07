"""app.ops.apis — ORM models.

API monitoring reuses the access log as the factual source of request counts,
latency and status distribution, and keeps an endpoint registry that gives those
raw facts a stable identity (method + normalised path).

Paths are stored **normalised**: a path parameter is replaced by a placeholder,
so a high cardinality of concrete ids can never explode the metric series and a
sensitive value can never be persisted.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsEndpoint(Base):
    """ops_endpoint — a monitored API endpoint."""

    __tablename__ = "ops_endpoint"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    endpoint_key: Mapped[str] = mapped_column(sa.String(255), nullable=False, comment="端点唯一键")
    http_method: Mapped[str] = mapped_column(sa.String(16), nullable=False, comment="HTTP 方法")
    path_pattern: Mapped[str] = mapped_column(
        sa.String(500), nullable=False, comment="归一化路径模板"
    )
    service_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_service.id"), nullable=True, comment="所属服务"
    )
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    is_monitored: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否纳入监控"
    )
    request_count: Mapped[int] = mapped_column(
        sa.BigInteger, nullable=False, server_default=sa.text("0"), comment="累计请求数"
    )
    error_count: Mapped[int] = mapped_column(
        sa.BigInteger, nullable=False, server_default=sa.text("0"), comment="累计错误数"
    )
    avg_latency_ms: Mapped[float | None] = mapped_column(
        sa.Float, nullable=True, comment="平均延迟毫秒"
    )
    p95_latency_ms: Mapped[float | None] = mapped_column(sa.Float, nullable=True,
        comment="P95 延迟毫秒")
    last_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="最近请求时间（UTC）"
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
        sa.UniqueConstraint("endpoint_key", name="uq_ops_endpoint_key"),
        sa.Index("ix_ops_endpoint_service", "service_id"),
        {"comment": "运维 API 端点"},
    )
