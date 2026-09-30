"""app.tools.access — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  tool_access_policy
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class ToolAccessPolicy(Base):
    """tool_access_policy — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_access_policy"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    subject_type: Mapped[str] = mapped_column(sa.String(32), comment="主体类型", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.true()
    )
    daily_limit: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="每日上限（NULL 表示不限）", nullable=True
    )
    rate_limit_per_minute: Mapped[int | None] = mapped_column(
        sa.Integer, comment="每分钟限流次数", nullable=True
    )
    concurrency_limit: Mapped[int | None] = mapped_column(
        sa.Integer, comment="并发上限", nullable=True
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
            "tool_id", "subject_type", name="tool_access_policy_tool_id_subject_type_key"
        ),
        {"comment": "工具访问策略"},
    )
