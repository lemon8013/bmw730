"""app.admin.dictionaries — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_dict_type, sys_dict_item
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class SysDictType(Base):
    """sys_dict_type — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_dict_type"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    dict_code: Mapped[str] = mapped_column(sa.String(128), comment="字典编码", nullable=False)
    dict_name: Mapped[str] = mapped_column(sa.String(128), comment="字典名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="字典状态（ACTIVE/DISABLED）",
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
            "uq_sys_dict_type_code",
            sa.text("lower(dict_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "数据字典类型"},
    )


class SysDictItem(Base):
    """sys_dict_item — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_dict_item"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    dict_type_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_dict_type.id"), comment="所属字典类型 ID", nullable=True
    )
    item_label: Mapped[str] = mapped_column(sa.String(128), comment="字典项显示名", nullable=False)
    item_value: Mapped[str] = mapped_column(sa.String(255), comment="字典项值", nullable=False)
    item_code: Mapped[str | None] = mapped_column(
        sa.String(128), comment="字典项编码", nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer,
        comment="排序序号（数值越小越靠前）",
        nullable=False,
        server_default=sa.text("0"),
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="字典项状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否默认项", nullable=False, server_default=sa.false()
    )
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
            "uq_sys_dict_item_value",
            "dict_type_id",
            "item_value",
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "数据字典项"},
    )
