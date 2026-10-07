"""app.ops.services — ORM models.

Monitored services and their dependency graph. The graph is what lets the UI
draw a topology and lets alert correlation avoid flooding downstream services
when a shared dependency fails.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsService(Base):
    """ops_service — a monitored service."""

    __tablename__ = "ops_service"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    service_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="服务编码")
    service_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="服务名称")
    service_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'APPLICATION'"),
        comment="服务类型（APPLICATION/DATABASE/CACHE/WEB/QUEUE）",
    )
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    host_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_host.id"), nullable=True, comment="承载主机"
    )
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'UNKNOWN'"),
        comment="服务状态（UP/DOWN/DEGRADED/UNKNOWN/MAINTENANCE）",
    )
    last_check_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="最近检查时间（UTC）"
    )
    availability_rate: Mapped[float | None] = mapped_column(
        sa.Float, nullable=True, comment="可用率"
    )
    error_rate: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="错误率")
    avg_latency_ms: Mapped[float | None] = mapped_column(
        sa.Float, nullable=True, comment="平均延迟毫秒"
    )
    tags: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
            comment="标签"
    )
    metadata_payload: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="结构化扩展属性",
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
        sa.UniqueConstraint("service_code", name="uq_ops_service_code"),
        sa.Index("ix_ops_service_status", "status"),
        sa.Index("ix_ops_service_environment", "environment"),
        {"comment": "运维服务"},
    )


class OpsServiceDependency(Base):
    """ops_service_dependency — directed edge of the service topology."""

    __tablename__ = "ops_service_dependency"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    service_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_service.id"), nullable=False, comment="依赖方服务"
    )
    depends_on_service_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_service.id"), nullable=False, comment="被依赖服务"
    )
    dependency_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'CALLS'"),
        comment="依赖类型（CALLS/USES/RUNS_ON）",
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
        sa.UniqueConstraint(
            "service_id", "depends_on_service_id", name="uq_ops_service_dependency_pair"
        ),
        sa.Index("ix_ops_service_dependency_target", "depends_on_service_id"),
        {"comment": "运维服务依赖"},
    )
