"""app.blog.interactions — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  blog_article_like, blog_article_favorite, blog_user_follow
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BlogArticleLike(Base):
    """blog_article_like — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_article_like"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_article.id"), comment="所属文章 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("user_id", "article_id", name="blog_article_like_pkey"),
        {"comment": "文章点赞"},
    )


class BlogArticleFavorite(Base):
    """blog_article_favorite — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_article_favorite"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_article.id"), comment="所属文章 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("user_id", "article_id", name="blog_article_favorite_pkey"),
        {"comment": "文章收藏"},
    )


class BlogUserFollow(Base):
    """blog_user_follow — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_user_follow"

    follower_user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="关注者用户 ID", nullable=False
    )
    followed_user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="被关注者用户 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "follower_user_id", "followed_user_id", name="blog_user_follow_pkey"
        ),
        sa.CheckConstraint("follower_user_id<>followed_user_id", name="blog_user_follow_check"),
        {"comment": "用户关注关系"},
    )
