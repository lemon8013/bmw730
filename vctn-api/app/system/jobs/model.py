"""app.system.jobs — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_job, sys_job_definition, sys_outbox_event, sys_idempotency_record
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysJob(Base):
    """sys_job — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_job"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    job_code: Mapped[str] = mapped_column(sa.String(128), comment="任务编码", nullable=False)
    job_name: Mapped[str] = mapped_column(sa.String(128), comment="任务名称", nullable=False)
    job_type: Mapped[str] = mapped_column(sa.String(64), comment="任务类型", nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, comment="业务载荷（JSONB）", nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="任务状态（PENDING/RUNNING/SUCCESS/FAILED/CANCELLED）",
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    priority: Mapped[int] = mapped_column(
        sa.Integer, comment="优先级（数值越大越优先）", nullable=False, server_default=sa.text("0")
    )
    attempt_count: Mapped[int] = mapped_column(
        sa.Integer, comment="已尝试次数", nullable=False, server_default=sa.text("0")
    )
    max_attempts: Mapped[int] = mapped_column(
        sa.Integer, comment="最大重试次数", nullable=False, server_default=sa.text("3")
    )
    available_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="可调度时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="开始执行时间（UTC）", nullable=True
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="结束执行时间（UTC）", nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(
        sa.Text, comment="最近一次错误信息", nullable=True
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="更新时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_sys_job_status_available", "status", "available_at"),
        {"comment": "后台异步任务"},
    )


class SysJobDefinition(Base):
    """sys_job_definition — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_job_definition"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    job_code: Mapped[str] = mapped_column(sa.String(128), comment="任务编码", nullable=False)
    job_name: Mapped[str] = mapped_column(sa.String(128), comment="任务名称", nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(
        sa.String(128), comment="Cron 表达式", nullable=True
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.true()
    )
    payload: Mapped[Any] = mapped_column(JSONB, comment="业务载荷（JSONB）", nullable=True)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="更新时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("job_code", name="sys_job_definition_job_code_key"),
        {"comment": "后台任务定义"},
    )


class SysOutboxEvent(Base):
    """sys_outbox_event — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_outbox_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    event_id: Mapped[str] = mapped_column(sa.String(128), comment="事件唯一 ID", nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(128), comment="事件类型", nullable=False)
    aggregate_type: Mapped[str | None] = mapped_column(
        sa.String(128), comment="聚合根类型", nullable=True
    )
    aggregate_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="聚合根 ID", nullable=True
    )
    payload: Mapped[Any] = mapped_column(JSONB, comment="业务载荷（JSONB）", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="投递状态（PENDING/PROCESSING/DONE/FAILED）",
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    attempt_count: Mapped[int] = mapped_column(
        sa.Integer, comment="已尝试次数", nullable=False, server_default=sa.text("0")
    )
    available_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="可调度时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    processed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="处理完成时间（UTC）", nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(
        sa.Text, comment="最近一次错误信息", nullable=True
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("event_id", name="sys_outbox_event_event_id_key"),
        sa.Index("idx_outbox_status_available", "status", "available_at"),
        {"comment": "事务性事件发件箱"},
    )


class SysIdempotencyRecord(Base):
    """sys_idempotency_record — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_idempotency_record"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), comment="幂等键", nullable=False)
    scope: Mapped[str] = mapped_column(sa.String(128), comment="幂等作用域", nullable=False)
    request_hash: Mapped[str] = mapped_column(
        sa.String(128), comment="请求指纹哈希", nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="处理状态（PROCESSING/DONE/FAILED）",
        nullable=False,
        server_default=sa.text("'PROCESSING'"),
    )
    response_code: Mapped[int | None] = mapped_column(
        sa.Integer, comment="缓存的响应状态码", nullable=True
    )
    response_body: Mapped[Any] = mapped_column(
        JSONB, comment="缓存的响应体（JSONB）", nullable=True
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), comment="过期时间（UTC）", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="更新时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "scope", "idempotency_key", name="sys_idempotency_record_scope_idempotency_key_key"
        ),
        {"comment": "接口幂等记录"},
    )
