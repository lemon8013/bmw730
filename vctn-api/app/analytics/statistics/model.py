"""app.analytics.statistics — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  behavior_event_daily, behavior_user_daily, behavior_page_daily, behavior_tool_daily,
    behavior_search_daily, behavior_funnel
"""

from __future__ import annotations

import datetime
import decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BehaviorEventDaily(Base):
    """behavior_event_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_event_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    total_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="总次数", nullable=False, server_default=sa.text("0")
    )
    unique_user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重用户数", nullable=False, server_default=sa.text("0")
    )
    unique_anonymous_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重匿名访客数", nullable=False, server_default=sa.text("0")
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
            "stat_date", "event_code", name="behavior_event_daily_stat_date_event_code_key"
        ),
        {"comment": "行为事件每日统计"},
    )


class BehaviorUserDaily(Base):
    """behavior_user_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_user_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="业务用户 ID（游客为 NULL）",
        nullable=True,
    )
    anonymous_id_hash: Mapped[str | None] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=True
    )
    event_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="事件次数", nullable=False, server_default=sa.text("0")
    )
    active: Mapped[bool] = mapped_column(
        sa.Boolean, comment="当日是否活跃", nullable=False, server_default=sa.true()
    )
    first_event_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="当日首次事件时间（UTC）", nullable=True
    )
    last_event_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="当日末次事件时间（UTC）", nullable=True
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
            "user_id",
            "anonymous_id_hash",
            name="behavior_user_daily_stat_date_user_id_anonymous_id_hash_key",
        ),
        {"comment": "用户每日活跃统计"},
    )


class BehaviorPageDaily(Base):
    """behavior_page_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_page_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    page_code: Mapped[str] = mapped_column(sa.String(128), comment="页面编码", nullable=False)
    view_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="浏览次数", nullable=False, server_default=sa.text("0")
    )
    unique_user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重用户数", nullable=False, server_default=sa.text("0")
    )
    unique_anonymous_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重匿名访客数", nullable=False, server_default=sa.text("0")
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
        sa.UniqueConstraint(
            "stat_date", "page_code", name="behavior_page_daily_stat_date_page_code_key"
        ),
        {"comment": "页面每日统计"},
    )


class BehaviorToolDaily(Base):
    """behavior_tool_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_tool_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    view_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="浏览次数", nullable=False, server_default=sa.text("0")
    )
    start_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="打开次数", nullable=False, server_default=sa.text("0")
    )
    execute_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="执行次数", nullable=False, server_default=sa.text("0")
    )
    success_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="成功次数", nullable=False, server_default=sa.text("0")
    )
    failure_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="失败次数", nullable=False, server_default=sa.text("0")
    )
    copy_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="复制次数", nullable=False, server_default=sa.text("0")
    )
    download_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="下载次数", nullable=False, server_default=sa.text("0")
    )
    unique_user_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="去重用户数", nullable=False, server_default=sa.text("0")
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
            "stat_date", "tool_id", name="behavior_tool_daily_stat_date_tool_id_key"
        ),
        {"comment": "工具每日行为统计"},
    )


class BehaviorSearchDaily(Base):
    """behavior_search_daily — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_search_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    stat_date: Mapped[datetime.date] = mapped_column(sa.Date, comment="统计日期", nullable=False)
    search_type: Mapped[str] = mapped_column(sa.String(64), comment="搜索类型", nullable=False)
    keyword_hash: Mapped[str] = mapped_column(sa.String(128), comment="关键词哈希", nullable=False)
    search_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="搜索次数", nullable=False, server_default=sa.text("0")
    )
    result_click_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="结果点击次数", nullable=False, server_default=sa.text("0")
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
            "search_type",
            "keyword_hash",
            name="behavior_search_daily_stat_date_search_type_keyword_hash_key",
        ),
        {"comment": "搜索每日统计"},
    )


class BehaviorFunnel(Base):
    """behavior_funnel — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_funnel"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    funnel_code: Mapped[str] = mapped_column(sa.String(128), comment="漏斗编码", nullable=False)
    funnel_name: Mapped[str] = mapped_column(sa.String(128), comment="漏斗名称", nullable=False)
    step_no: Mapped[int] = mapped_column(sa.Integer, comment="步骤序号", nullable=False)
    step_code: Mapped[str] = mapped_column(sa.String(128), comment="步骤编码", nullable=False)
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.true()
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
            "funnel_code", "step_no", name="behavior_funnel_funnel_code_step_no_key"
        ),
        {"comment": "转化漏斗定义"},
    )
