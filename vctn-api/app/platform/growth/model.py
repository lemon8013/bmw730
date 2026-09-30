"""app.platform.growth — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  biz_growth_rule, biz_growth_event, biz_user_growth_transaction, biz_user_growth_account,
    biz_task, biz_user_task, biz_achievement, biz_user_achievement
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BizGrowthRule(Base):
    """biz_growth_rule — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_growth_rule"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    rule_code: Mapped[str] = mapped_column(sa.String(128), comment="规则编码", nullable=False)
    rule_name: Mapped[str] = mapped_column(sa.String(128), comment="规则名称", nullable=False)
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    growth_points: Mapped[int] = mapped_column(sa.BigInteger, comment="成长值", nullable=False)
    daily_limit: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="每日上限（NULL 表示不限）", nullable=True
    )
    cooldown_seconds: Mapped[int | None] = mapped_column(
        sa.Integer, comment="冷却时间（秒）", nullable=True
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.true()
    )
    conditions: Mapped[Any] = mapped_column(JSONB, comment="生效条件（JSONB）", nullable=True)
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
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="软删除时间（UTC，NULL 表示未删除）", nullable=True
    )

    __table_args__ = (
        sa.Index(
            "uq_growth_rule_code",
            sa.text("lower(rule_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "成长值发放规则"},
    )


class BizGrowthEvent(Base):
    """biz_growth_event — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "biz_growth_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    event_id: Mapped[str] = mapped_column(sa.String(128), comment="事件唯一 ID", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), comment="幂等键", nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    source_type: Mapped[str] = mapped_column(sa.String(64), comment="来源类型", nullable=False)
    source_id: Mapped[str | None] = mapped_column(sa.String(128), comment="来源 ID", nullable=True)
    growth_points: Mapped[int] = mapped_column(sa.BigInteger, comment="成长值", nullable=False)
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="事件发生时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("event_id", name="biz_growth_event_event_id_key"),
        sa.UniqueConstraint("idempotency_key", name="biz_growth_event_idempotency_key_key"),
        {"comment": "成长值事件"},
    )


class BizUserGrowthTransaction(Base):
    """biz_user_growth_transaction — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_growth_transaction"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    event_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_growth_event.id"), comment="事件唯一 ID", nullable=True
    )
    delta_points: Mapped[int] = mapped_column(
        sa.BigInteger, comment="变动积分（正数获得、负数消耗）", nullable=False
    )
    balance_after: Mapped[int] = mapped_column(sa.BigInteger, comment="变动后余额", nullable=False)
    transaction_type: Mapped[str] = mapped_column(sa.String(32), comment="流水类型", nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(255), comment="原因说明", nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "成长值流水"},)


class BizUserGrowthAccount(Base):
    """biz_user_growth_account — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_growth_account"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="业务用户 ID（同时作为主键）",
        primary_key=True,
        autoincrement=False,
    )
    total_growth_points: Mapped[int] = mapped_column(
        sa.BigInteger, comment="累计成长值", nullable=False, server_default=sa.text("0")
    )
    current_level_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user_level.id"), comment="当前等级 ID", nullable=True
    )
    version: Mapped[int] = mapped_column(
        sa.BigInteger, comment="乐观锁版本号", nullable=False, server_default=sa.text("0")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="更新时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "用户成长值账户"},)


class BizTask(Base):
    """biz_task — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_task"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    task_code: Mapped[str] = mapped_column(sa.String(128), comment="任务编码", nullable=False)
    task_name: Mapped[str] = mapped_column(sa.String(128), comment="任务名称", nullable=False)
    task_type: Mapped[str] = mapped_column(sa.String(32), comment="任务类型", nullable=False)
    conditions: Mapped[Any] = mapped_column(JSONB, comment="生效条件（JSONB）", nullable=False)
    reward: Mapped[Any] = mapped_column(JSONB, comment="奖励配置（JSONB）", nullable=True)
    start_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="开始时间（UTC）", nullable=True
    )
    end_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="结束时间（UTC）", nullable=True
    )
    repeatable: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否可重复完成", nullable=False, server_default=sa.false()
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="任务状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
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
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="软删除时间（UTC，NULL 表示未删除）", nullable=True
    )

    __table_args__ = (
        sa.Index(
            "uq_task_code",
            sa.text("lower(task_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "任务定义"},
    )


class BizUserTask(Base):
    """biz_user_task — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_task"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_task.id"), comment="任务 ID", nullable=True
    )
    progress: Mapped[Any] = mapped_column(JSONB, comment="任务进度（JSONB）", nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="任务进度状态（IN_PROGRESS/COMPLETED/EXPIRED）",
        nullable=False,
        server_default=sa.text("'IN_PROGRESS'"),
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="完成时间（UTC）", nullable=True
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
        sa.UniqueConstraint("user_id", "task_id", name="biz_user_task_user_id_task_id_key"),
        {"comment": "用户任务进度"},
    )


class BizAchievement(Base):
    """biz_achievement — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_achievement"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    achievement_code: Mapped[str] = mapped_column(
        sa.String(128), comment="成就编码", nullable=False
    )
    achievement_name: Mapped[str] = mapped_column(
        sa.String(128), comment="成就名称", nullable=False
    )
    conditions: Mapped[Any] = mapped_column(JSONB, comment="生效条件（JSONB）", nullable=False)
    reward: Mapped[Any] = mapped_column(JSONB, comment="奖励配置（JSONB）", nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="成就状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
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
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="软删除时间（UTC，NULL 表示未删除）", nullable=True
    )

    __table_args__ = (
        sa.Index(
            "uq_achievement_code",
            sa.text("lower(achievement_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "成就定义"},
    )


class BizUserAchievement(Base):
    """biz_user_achievement — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_achievement"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    achievement_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_achievement.id"), comment="成就 ID", nullable=True
    )
    achieved_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="达成时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "achievement_id", name="biz_user_achievement_user_id_achievement_id_key"
        ),
        {"comment": "用户已达成成就"},
    )
