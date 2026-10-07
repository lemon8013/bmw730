"""app.ops.audit — ORM models.

``sys_audit_log`` remains the authoritative, append-only audit trail. This table
is the **ops readable** projection of ops operations: same facts, but queryable
and pageable inside the ops UI without reaching into the system audit tables.

Every row is append-only: the service layer only ever inserts.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsOperationRecord(Base):
    """ops_operation_record — one recorded ops action."""

    __tablename__ = "ops_operation_record"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    operator_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="操作人")
    operator_username: Mapped[str | None] = mapped_column(sa.String(64), nullable=True,
        comment="操作人账号")
    action: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="操作动作")
    resource_type: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="资源类型")
    resource_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="资源 ID")
    result: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'SUCCESS'"),
        comment="操作结果（SUCCESS/FAILURE）",
    )
    error_message: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True,
        comment="错误信息")
    ip_address: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="操作 IP")
    user_agent: Mapped[str | None] = mapped_column(sa.String(500), nullable=True, comment="操作 UA")
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="链路追踪 ID"
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, comment="请求 ID")
    before_data: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
            comment="变更前数据"
    )
    after_data: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
            comment="变更后数据"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_operation_record_action_time", "action", "created_at"),
        sa.Index("ix_ops_operation_record_operator", "operator_id"),
        sa.Index("ix_ops_operation_record_trace", "trace_id"),
        {"comment": "运维操作记录"},
    )
