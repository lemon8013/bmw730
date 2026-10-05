"""app.tools.usage — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  tool_usage_event, tool_recent_usage
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class ToolUsageEvent(Base):
    """tool_usage_event — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_usage_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    tool_version_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tool_version.id"),
        comment="执行时使用的工具版本 ID",
        nullable=True,
    )
    subject_type: Mapped[str] = mapped_column(sa.String(32), comment="主体类型", nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="使用者业务用户 ID（游客为 NULL）",
        nullable=True,
    )
    anonymous_id_hash: Mapped[str | None] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=True
    )
    execution_mode: Mapped[str] = mapped_column(sa.String(32), comment="执行模式", nullable=False)
    success: Mapped[bool] = mapped_column(sa.Boolean, comment="是否成功", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="耗时（毫秒）", nullable=True
    )
    source: Mapped[str | None] = mapped_column(sa.String(64), comment="来源标识", nullable=True)
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(128), comment="请求 ID", nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_tool_usage_tool_time", "tool_id", sa.text("created_at DESC")),
        {"comment": "工具使用事件"},
    )


class ToolRecentUsage(Base):
    """tool_recent_usage — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_recent_usage"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    last_used_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="最近使用时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    use_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="累计使用次数", nullable=False, server_default=sa.text("1")
    )

    __table_args__ = (
        sa.UniqueConstraint("user_id", "tool_id", name="tool_recent_usage_user_id_tool_id_key"),
        {"comment": "用户最近使用的工具"},
    )
