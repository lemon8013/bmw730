"""app.blog.authors — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  blog_author, blog_author_application
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BlogAuthor(Base):
    """blog_author — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_author"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=False
    )
    author_name: Mapped[str] = mapped_column(sa.String(128), comment="作者名", nullable=False)
    bio: Mapped[str | None] = mapped_column(sa.String(1000), comment="个人简介", nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, comment="头像地址", nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="作者状态（ACTIVE/SUSPENDED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    approved_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="审核通过时间（UTC）", nullable=True
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
        sa.UniqueConstraint("user_id", name="blog_author_user_id_key"),
        {"comment": "博客作者"},
    )


class BlogAuthorApplication(Base):
    """blog_author_application — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_author_application"

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
    application_reason: Mapped[str | None] = mapped_column(
        sa.Text, comment="申请理由", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="申请状态（PENDING/APPROVED/REJECTED）",
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    reviewer_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("sys_user.id"),
        comment="审核人 ID（后台管理员）",
        nullable=True,
    )
    review_reason: Mapped[str | None] = mapped_column(
        sa.String(1000), comment="审核意见", nullable=True
    )
    applied_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="申请时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="审核时间（UTC）", nullable=True
    )

    __table_args__ = ({"comment": "博客作者申请"},)
