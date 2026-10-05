"""app.platform.levels — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  biz_user_level, biz_user_level_history, biz_user_level_benefit
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BizUserLevel(Base):
    """biz_user_level — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_level"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    level_code: Mapped[str] = mapped_column(sa.String(64), comment="等级编码", nullable=False)
    level_name: Mapped[str] = mapped_column(sa.String(128), comment="等级名称", nullable=False)
    level_no: Mapped[int] = mapped_column(sa.Integer, comment="等级序号", nullable=False)
    min_growth_points: Mapped[int] = mapped_column(
        sa.BigInteger, comment="升到该等级所需最小成长值", nullable=False
    )
    max_growth_points: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="该等级成长值上限", nullable=True
    )
    icon_url: Mapped[str | None] = mapped_column(sa.Text, comment="图标地址", nullable=True)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="等级状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer,
        comment="排序序号（数值越小越靠前）",
        nullable=False,
        server_default=sa.text("0"),
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
        sa.UniqueConstraint("level_no", name="biz_user_level_level_no_key"),
        {"comment": "用户等级定义"},
    )


class BizUserLevelHistory(Base):
    """biz_user_level_history — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_level_history"

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
    from_level_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user_level.id"), comment="变更前的等级 ID", nullable=True
    )
    to_level_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user_level.id"), comment="变更后的等级 ID", nullable=True
    )
    growth_points: Mapped[int] = mapped_column(sa.BigInteger, comment="成长值", nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.String(255), comment="原因说明", nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "用户等级变更历史"},)


class BizUserLevelBenefit(Base):
    """biz_user_level_benefit — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_level_benefit"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    level_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user_level.id"), comment="所属等级 ID", nullable=True
    )
    benefit_type: Mapped[str] = mapped_column(sa.String(64), comment="权益类型", nullable=False)
    benefit_code: Mapped[str] = mapped_column(sa.String(128), comment="权益编码", nullable=False)
    benefit_value: Mapped[Any] = mapped_column(JSONB, comment="权益值（JSONB）", nullable=True)
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
            "level_id",
            "benefit_type",
            "benefit_code",
            name="biz_user_level_benefit_level_id_benefit_type_benefit_code_key",
        ),
        {"comment": "等级权益"},
    )
