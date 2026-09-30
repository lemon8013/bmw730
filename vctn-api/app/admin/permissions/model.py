"""app.admin.permissions — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_permission, sys_role_permission, sys_permission_field
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysPermission(Base):
    """sys_permission — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    permission_code: Mapped[str] = mapped_column(sa.String(128), comment="权限编码", nullable=False)
    permission_name: Mapped[str] = mapped_column(sa.String(128), comment="权限名称", nullable=False)
    permission_type: Mapped[str] = mapped_column(sa.String(32), comment="权限类型", nullable=False)
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(64), comment="资源类型", nullable=True
    )
    resource_code: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源编码", nullable=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_permission.id"), comment="父级 ID", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="权限状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer,
        comment="排序序号（数值越小越靠前）",
        nullable=False,
        server_default=sa.text("0"),
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
            "uq_sys_permission_code",
            sa.text("lower(permission_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "后台权限定义"},
    )


class SysRolePermission(Base):
    """sys_role_permission — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_role_permission"

    role_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_role.id"), comment="角色 ID", nullable=False
    )
    permission_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_permission.id"), comment="权限 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="sys_role_permission_pkey"),
        {"comment": "后台角色与权限关联"},
    )


class SysPermissionField(Base):
    """sys_permission_field — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_permission_field"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    permission_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_permission.id"), comment="权限 ID", nullable=True
    )
    field_code: Mapped[str] = mapped_column(sa.String(128), comment="字段编码", nullable=False)
    field_mode: Mapped[str] = mapped_column(sa.String(32), comment="字段控制模式", nullable=False)
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
            "permission_id", "field_code", name="sys_permission_field_permission_id_field_code_key"
        ),
        {"comment": "后台权限字段级控制"},
    )
