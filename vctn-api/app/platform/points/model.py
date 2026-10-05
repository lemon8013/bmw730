"""app.platform.points — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  biz_point_rule, biz_point_transaction, biz_user_point_account
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BizPointRule(Base):
    """biz_point_rule — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_point_rule"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    rule_code: Mapped[str] = mapped_column(sa.String(128), comment="规则编码", nullable=False)
    rule_name: Mapped[str] = mapped_column(sa.String(128), comment="规则名称", nullable=False)
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    points: Mapped[int] = mapped_column(sa.BigInteger, comment="积分变动值", nullable=False)
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
            "uq_point_rule_code",
            sa.text("lower(rule_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "积分发放规则"},
    )


class BizPointTransaction(Base):
    """biz_point_transaction — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "biz_point_transaction"

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
    event_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="事件唯一 ID", nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        sa.String(255), comment="幂等键", nullable=True
    )
    delta_points: Mapped[int] = mapped_column(
        sa.BigInteger, comment="变动积分（正数获得、负数消耗）", nullable=False
    )
    balance_after: Mapped[int] = mapped_column(sa.BigInteger, comment="变动后余额", nullable=False)
    transaction_type: Mapped[str] = mapped_column(sa.String(32), comment="流水类型", nullable=False)
    source_type: Mapped[str | None] = mapped_column(
        sa.String(64), comment="来源类型", nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(sa.String(128), comment="来源 ID", nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.String(255), comment="原因说明", nullable=True)
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index(
            "uq_point_tx_idempotency",
            "idempotency_key",
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        ),
        {"comment": "积分流水"},
    )


class BizUserPointAccount(Base):
    """biz_user_point_account — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_point_account"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="业务用户 ID（同时作为主键）",
        primary_key=True,
        autoincrement=False,
    )
    balance: Mapped[int] = mapped_column(
        sa.BigInteger, comment="当前积分余额", nullable=False, server_default=sa.text("0")
    )
    total_earned: Mapped[int] = mapped_column(
        sa.BigInteger, comment="累计获得积分", nullable=False, server_default=sa.text("0")
    )
    total_spent: Mapped[int] = mapped_column(
        sa.BigInteger, comment="累计消耗积分", nullable=False, server_default=sa.text("0")
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

    __table_args__ = (
        sa.CheckConstraint("balance>=0", name="biz_user_point_account_balance_check"),
        {"comment": "用户积分账户"},
    )
