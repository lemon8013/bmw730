"""app.ops.hosts — ORM models.

Ops monitoring infrastructure: environment, host and host group.

The DDL baseline (``aicoding/sql/vctn-enterprise-ddl-v2.0.sql``) does not cover
the ops domain, so these tables are introduced with the ops module and are
created by their own Alembic revision. Every table follows the frozen baseline
conventions: BIGINT snowflake identifiers, UTC timestamps, soft delete via
``deleted_at`` and no ``tenant_id`` (single organisation model).
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsEnvironment(Base):
    """ops_environment — deployment environment."""

    __tablename__ = "ops_environment"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    env_code: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, comment="环境编码（PRODUCTION/STAGING/TEST/DEVELOPMENT）"
    )
    env_name: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="环境名称")
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True, comment="描述说明"
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="排序序号"
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
        sa.UniqueConstraint("env_code", name="uq_ops_environment_code"),
        {"comment": "运维环境"},
    )


class OpsHostGroup(Base):
    """ops_host_group — a grouping of monitored hosts."""

    __tablename__ = "ops_host_group"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    group_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="分组编码")
    group_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="分组名称")
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True, comment="描述说明"
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="排序序号"
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
        sa.UniqueConstraint("group_code", name="uq_ops_host_group_code"),
        {"comment": "运维主机分组"},
    )


class OpsHost(Base):
    """ops_host — a monitored physical, virtual or container host."""

    __tablename__ = "ops_host"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    hostname: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="主机名")
    display_name: Mapped[str | None] = mapped_column(
        sa.String(128), nullable=True, comment="展示名称"
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="IP 地址")
    os_type: Mapped[str | None] = mapped_column(
        sa.String(32), nullable=True, comment="操作系统类型"
    )
    os_version: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="操作系统版本"
    )
    cpu_cores: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, comment="CPU 核数")
    memory_total_mb: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True,
        comment="内存总量 MB")
    disk_total_gb: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True,
        comment="磁盘总量 GB")
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    host_group_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_host_group.id"), nullable=True, comment="所属主机分组"
    )
    # Deliberately **not** a foreign key: ``ops_agent.host_id`` already points
    # at ``ops_host``, and a second constraint in the opposite direction would
    # make the two tables mutually dependent, which Alembic cannot order. The
    # association is resolved in the service layer instead.
    agent_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="关联采集 Agent"
    )
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'UNKNOWN'"),
        comment="主机状态（ONLINE/OFFLINE/UNKNOWN/MAINTENANCE）",
    )
    last_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="最后上报时间（UTC）"
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
        sa.UniqueConstraint("hostname", name="uq_ops_host_hostname"),
        sa.Index("ix_ops_host_status", "status"),
        sa.Index("ix_ops_host_environment", "environment"),
        {"comment": "运维主机"},
    )
