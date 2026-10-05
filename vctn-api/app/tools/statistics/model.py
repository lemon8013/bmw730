"""app.tools.statistics — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  tool_usage_daily, tool_popularity_daily
"""

from __future__ import annotations

import datetime
import decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class ToolUsageDaily(Base):
    """tool_usage_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_usage_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    total_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="总次数", nullable=False, server_default=sa.text("0")
    )
    success_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="成功次数", nullable=False, server_default=sa.text("0")
    )
    failure_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="失败次数", nullable=False, server_default=sa.text("0")
    )
    guest_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="游客使用次数", nullable=False, server_default=sa.text("0")
    )
    user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="登录用户使用次数", nullable=False, server_default=sa.text("0")
    )
    unique_user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重用户数", nullable=False, server_default=sa.text("0")
    )
    unique_guest_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重游客数", nullable=False, server_default=sa.text("0")
    )
    avg_duration_ms: Mapped[decimal.Decimal | None] = mapped_column(
        sa.Numeric(18, 2), comment="平均耗时（毫秒）", nullable=True
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
        sa.UniqueConstraint("stat_date", "tool_id", name="tool_usage_daily_stat_date_tool_id_key"),
        {"comment": "工具每日使用统计"},
    )


class ToolPopularityDaily(Base):
    """tool_popularity_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_popularity_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    window_days: Mapped[int] = mapped_column(sa.Integer, comment="统计窗口天数", nullable=False)
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    usage_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="使用次数", nullable=False, server_default=sa.text("0")
    )
    unique_user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重用户数", nullable=False, server_default=sa.text("0")
    )
    rank_no: Mapped[int | None] = mapped_column(sa.Integer, comment="排名", nullable=True)
    score: Mapped[decimal.Decimal | None] = mapped_column(
        sa.Numeric(20, 6), comment="热度评分", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "stat_date",
            "window_days",
            "tool_id",
            name="tool_popularity_daily_stat_date_window_days_tool_id_key",
        ),
        {"comment": "工具每日热度排行"},
    )
