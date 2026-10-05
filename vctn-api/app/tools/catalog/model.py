"""app.tools.catalog — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  tool_category, tool, tool_version, tool_component_registry
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class ToolCategory(Base):
    """tool_category — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_category"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    category_code: Mapped[str] = mapped_column(sa.String(64), comment="分类编码", nullable=False)
    category_name: Mapped[str] = mapped_column(sa.String(128), comment="分类名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    icon_url: Mapped[str | None] = mapped_column(sa.Text, comment="图标地址", nullable=True)
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

    __table_args__ = (
        sa.Index(
            "uq_tool_category_code",
            sa.text("lower(category_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "工具分类"},
    )


class Tool(Base):
    """tool — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    code: Mapped[str] = mapped_column(sa.String(128), comment="工具编码", nullable=False)
    name: Mapped[str] = mapped_column(sa.String(128), comment="工具名称", nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(160), comment="URL 别名", nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool_category.id"), comment="所属分类 ID", nullable=True
    )
    icon: Mapped[str | None] = mapped_column(sa.Text, comment="图标", nullable=True)
    summary: Mapped[str | None] = mapped_column(sa.String(500), comment="摘要", nullable=True)
    description: Mapped[str | None] = mapped_column(sa.Text, comment="描述说明", nullable=True)
    keywords: Mapped[Any] = mapped_column(JSONB, comment="搜索关键词（JSONB 数组）", nullable=True)
    tags: Mapped[Any] = mapped_column(JSONB, comment="标签（JSONB 数组）", nullable=True)
    component_key: Mapped[str] = mapped_column(
        sa.String(128), comment="组件唯一标识", nullable=False
    )
    execution_mode: Mapped[str] = mapped_column(sa.String(32), comment="执行模式", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="工具状态（DRAFT/PUBLISHED/OFFLINE/DEPRECATED）",
        nullable=False,
        server_default=sa.text("'DRAFT'"),
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer,
        comment="排序序号（数值越小越靠前）",
        nullable=False,
        server_default=sa.text("0"),
    )
    current_version_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("tool_version.id", name="fk_tool_current_version", use_alter=True),
        comment="当前生效版本 ID",
        nullable=True,
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
            "uq_tool_code",
            sa.text("lower(code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        sa.Index(
            "uq_tool_slug",
            sa.text("lower(slug)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "工具"},
    )


class ToolVersion(Base):
    """tool_version — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_version"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    tool_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("tool.id"), comment="所属工具 ID", nullable=True
    )
    version: Mapped[str] = mapped_column(sa.String(64), comment="乐观锁版本号", nullable=False)
    release_status: Mapped[str] = mapped_column(
        sa.String(32), comment="发布状态", nullable=False, server_default=sa.text("'DRAFT'")
    )
    changelog: Mapped[str | None] = mapped_column(sa.Text, comment="版本变更说明", nullable=True)
    runtime_config: Mapped[Any] = mapped_column(JSONB, comment="运行时配置（JSONB）", nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    published_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="发布时间（UTC）", nullable=True
    )

    __table_args__ = (
        sa.UniqueConstraint("tool_id", "version", name="tool_version_tool_id_version_key"),
        {"comment": "工具版本"},
    )


class ToolComponentRegistry(Base):
    """tool_component_registry — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "tool_component_registry"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    component_key: Mapped[str] = mapped_column(
        sa.String(128), comment="组件唯一标识", nullable=False
    )
    component_name: Mapped[str] = mapped_column(sa.String(128), comment="组件名称", nullable=False)
    frontend_component_key: Mapped[str] = mapped_column(
        sa.String(255), comment="前端组件标识", nullable=False
    )
    execution_mode: Mapped[str] = mapped_column(sa.String(32), comment="执行模式", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16), comment="状态", nullable=False, server_default=sa.text("'ACTIVE'")
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
        sa.UniqueConstraint("component_key", name="tool_component_registry_component_key_key"),
        {"comment": "工具前端组件注册表"},
    )
