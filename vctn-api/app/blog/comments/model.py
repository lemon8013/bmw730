"""app.blog.comments — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  blog_comment
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BlogComment(Base):
    """blog_comment — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_comment"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    article_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_article.id"), comment="所属文章 ID", nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_comment.id"), comment="父级 ID", nullable=True
    )
    content: Mapped[str] = mapped_column(sa.Text, comment="内容", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="评论状态（PENDING/APPROVED/REJECTED）",
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("sys_user.id"),
        comment="审核人 ID（后台管理员）",
        nullable=True,
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="审核时间（UTC）", nullable=True
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

    __table_args__ = ({"comment": "文章评论"},)
