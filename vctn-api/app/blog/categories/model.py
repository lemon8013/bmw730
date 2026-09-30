"""app.blog.categories — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  blog_category
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BlogCategory(Base):
    """blog_category — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_category"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    category_code: Mapped[str] = mapped_column(sa.String(64), comment="分类编码", nullable=False)
    category_name: Mapped[str] = mapped_column(sa.String(128), comment="分类名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer,
        comment="排序序号（数值越小越靠前）",
        nullable=False,
        server_default=sa.text("0"),
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="分类状态（ACTIVE/DISABLED）",
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

    __table_args__ = ({"comment": "博客分类"},)
