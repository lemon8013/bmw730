"""app.platform.cosmetics — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  biz_cosmetic, biz_user_cosmetic, biz_user_equipment
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BizCosmetic(Base):
    """biz_cosmetic — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "biz_cosmetic"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    cosmetic_code: Mapped[str] = mapped_column(sa.String(128), comment="装扮编码", nullable=False)
    cosmetic_name: Mapped[str] = mapped_column(sa.String(128), comment="装扮名称", nullable=False)
    cosmetic_type: Mapped[str] = mapped_column(sa.String(32), comment="装扮类型", nullable=False)
    asset_url: Mapped[str | None] = mapped_column(sa.Text, comment="素材地址", nullable=True)
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="装扮状态（ACTIVE/DISABLED）",
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
        sa.Index(
            "uq_cosmetic_code",
            sa.text("lower(cosmetic_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "装扮道具"},
    )


class BizUserCosmetic(Base):
    """biz_user_cosmetic — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_cosmetic"

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
    cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="装扮 ID", nullable=True
    )
    obtained_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="获得时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    source_type: Mapped[str | None] = mapped_column(
        sa.String(64), comment="来源类型", nullable=True
    )
    source_id: Mapped[str | None] = mapped_column(sa.String(128), comment="来源 ID", nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "cosmetic_id", name="biz_user_cosmetic_user_id_cosmetic_id_key"
        ),
        {"comment": "用户已获得的装扮"},
    )


class BizUserEquipment(Base):
    """biz_user_equipment — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_equipment"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="业务用户 ID（同时作为主键）",
        primary_key=True,
        autoincrement=False,
    )
    avatar_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="头像装扮 ID", nullable=True
    )
    avatar_frame_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="头像框装扮 ID", nullable=True
    )
    crown_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="皇冠装扮 ID", nullable=True
    )
    badge_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="徽章装扮 ID", nullable=True
    )
    title_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="称号装扮 ID", nullable=True
    )
    name_effect_cosmetic_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_cosmetic.id"), comment="昵称特效装扮 ID", nullable=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="更新时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "用户装扮装备"},)
