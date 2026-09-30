"""app.admin.audit — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_audit_log, sys_access_log, sys_security_log, sys_operation_log, sys_application_log
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysAuditLog(Base):
    """sys_audit_log — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_audit_log"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(128), comment="请求 ID", nullable=True)
    operator_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="操作人 ID", nullable=True
    )
    operator_username: Mapped[str | None] = mapped_column(
        sa.String(64), comment="操作人用户名（冗余快照）", nullable=True
    )
    action: Mapped[str] = mapped_column(sa.String(128), comment="命中后的处理动作", nullable=False)
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源类型", nullable=True
    )
    resource_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源 ID", nullable=True
    )
    before_data: Mapped[Any] = mapped_column(JSONB, comment="变更前数据（JSONB）", nullable=True)
    after_data: Mapped[Any] = mapped_column(JSONB, comment="变更后数据（JSONB）", nullable=True)
    result: Mapped[str] = mapped_column(sa.String(32), comment="结果", nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64), comment="错误码", nullable=True)
    ip: Mapped[Any] = mapped_column(INET, comment="IP 地址", nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text, comment="客户端 User-Agent", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_audit_resource", "resource_type", "resource_id", sa.text("created_at DESC")),
        sa.Index("idx_audit_trace", "trace_id"),
        {"comment": "审计日志"},
    )


class SysAccessLog(Base):
    """sys_access_log — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_access_log"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(128), comment="请求 ID", nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="访问者用户 ID（未登录为 NULL）", nullable=True
    )
    method: Mapped[str] = mapped_column(sa.String(16), comment="HTTP 方法", nullable=False)
    path: Mapped[str] = mapped_column(sa.Text, comment="请求路径", nullable=False)
    status_code: Mapped[int | None] = mapped_column(
        sa.Integer, comment="HTTP 响应状态码", nullable=True
    )
    ip: Mapped[Any] = mapped_column(INET, comment="IP 地址", nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text, comment="客户端 User-Agent", nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="耗时（毫秒）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "访问日志"},)


class SysSecurityLog(Base):
    """sys_security_log — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "sys_security_log"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="关联用户 ID（未登录为 NULL）", nullable=True
    )
    event_type: Mapped[str] = mapped_column(sa.String(128), comment="事件类型", nullable=False)
    result: Mapped[str] = mapped_column(sa.String(32), comment="结果", nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64), comment="错误码", nullable=True)
    ip: Mapped[Any] = mapped_column(INET, comment="IP 地址", nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text, comment="客户端 User-Agent", nullable=True
    )
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "安全日志"},)


class SysOperationLog(Base):
    """sys_operation_log — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "sys_operation_log"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(128), comment="请求 ID", nullable=True)
    operator_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="操作人 ID", nullable=True
    )
    operation: Mapped[str] = mapped_column(sa.String(128), comment="操作名称", nullable=False)
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源类型", nullable=True
    )
    resource_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源 ID", nullable=True
    )
    result: Mapped[str] = mapped_column(sa.String(32), comment="结果", nullable=False)
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "操作日志"},)


class SysApplicationLog(Base):
    """sys_application_log — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "sys_application_log"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    level: Mapped[str] = mapped_column(sa.String(16), comment="日志级别", nullable=False)
    logger_name: Mapped[str | None] = mapped_column(
        sa.String(255), comment="日志器名称", nullable=True
    )
    message: Mapped[str] = mapped_column(sa.Text, comment="日志消息", nullable=False)
    exception_type: Mapped[str | None] = mapped_column(
        sa.String(255), comment="异常类型", nullable=True
    )
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "应用日志"},)
