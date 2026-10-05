"""app.blog.articles — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  blog_article, blog_article_tag
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BlogArticle(Base):
    """blog_article — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_article"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    author_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_author.id"), comment="作者 ID", nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("blog_category.id"), comment="所属分类 ID", nullable=True
    )
    title: Mapped[str] = mapped_column(sa.String(255), comment="标题", nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(255), comment="URL 别名", nullable=False)
    summary: Mapped[str | None] = mapped_column(sa.String(1000), comment="摘要", nullable=True)
    cover_url: Mapped[str | None] = mapped_column(sa.Text, comment="封面图地址", nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(
        sa.Text, comment="正文 Markdown 源码", nullable=True
    )
    content_html: Mapped[str | None] = mapped_column(
        sa.Text, comment="正文渲染后的 HTML", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="文章状态（DRAFT/PUBLISHED/OFFLINE）",
        nullable=False,
        server_default=sa.text("'DRAFT'"),
    )
    review_status: Mapped[str] = mapped_column(
        sa.String(32), comment="审核状态", nullable=False, server_default=sa.text("'NOT_REQUIRED'")
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
    published_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="发布时间（UTC）", nullable=True
    )
    view_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="浏览次数", nullable=False, server_default=sa.text("0")
    )
    like_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="点赞数", nullable=False, server_default=sa.text("0")
    )
    favorite_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="收藏数", nullable=False, server_default=sa.text("0")
    )
    comment_count: Mapped[int] = mapped_column(
        sa.BigInteger, comment="评论数", nullable=False, server_default=sa.text("0")
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
            "uq_blog_article_slug",
            sa.text("lower(slug)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "博客文章"},
    )


class BlogArticleTag(Base):
    """blog_article_tag — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "blog_article_tag"

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
    tag_name: Mapped[str] = mapped_column(sa.String(128), comment="标签名", nullable=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "article_id", "tag_name", name="blog_article_tag_article_id_tag_name_key"
        ),
        {"comment": "文章标签"},
    )
