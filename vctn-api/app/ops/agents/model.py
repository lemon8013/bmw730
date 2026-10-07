"""app.ops.agents — ORM models.

Agent registration and heartbeats. The agent credential is stored **hashed
only**: a plain agent token is never persisted, so it can never leak through a
log, an export or an API response.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsAgent(Base):
    """ops_agent — a registered collection agent."""

    __tablename__ = "ops_agent"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    agent_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="Agent 编码")
    agent_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="Agent 名称")
    host_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_host.id"), nullable=True, comment="所属主机"
    )
    token_hash: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="Agent 凭证哈希（明文永不落库）"
    )
    version: Mapped[str | None] = mapped_column(sa.String(32), nullable=True, comment="Agent 版本")
    ip_address: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="上报 IP")
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'UNKNOWN'"),
        comment="Agent 状态（ONLINE/OFFLINE/UPGRADING/UNKNOWN）",
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
    last_heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="最后心跳时间（UTC）"
    )
    registered_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="注册时间（UTC）"
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
        sa.UniqueConstraint("agent_code", name="uq_ops_agent_code"),
        sa.Index("ix_ops_agent_status", "status"),
        {"comment": "运维采集 Agent"},
    )


class OpsAgentHeartbeat(Base):
    """ops_agent_heartbeat — one heartbeat payload reported by an agent."""

    __tablename__ = "ops_agent_heartbeat"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    agent_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_agent.id"), nullable=False, comment="所属 Agent"
    )
    cpu_usage: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="CPU 使用率")
    memory_usage: Mapped[float | None] = mapped_column(
        sa.Float, nullable=True, comment="内存使用率"
    )
    disk_usage: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="磁盘使用率")
    load1: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="Load 1")
    load5: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="Load 5")
    load15: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="Load 15")
    net_rx_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True,
        comment="网络入流量字节")
    net_tx_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True,
        comment="网络出流量字节")
    uptime_seconds: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True,
        comment="运行时长秒")
    collected_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="采集时间（UTC）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_agent_heartbeat_agent_collected", "agent_id", "collected_at"),
        {"comment": "运维 Agent 心跳"},
    )
