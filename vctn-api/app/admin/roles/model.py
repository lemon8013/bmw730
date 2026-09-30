"""app.admin.roles — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_role, sys_user_role, sys_role_inheritance, sys_role_data_scope
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysRole(Base):
    """sys_role — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    role_code: Mapped[str] = mapped_column(sa.String(64), comment="角色编码", nullable=False)
    role_name: Mapped[str] = mapped_column(sa.String(128), comment="角色名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="角色状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    data_scope: Mapped[str] = mapped_column(
        sa.String(32), comment="数据范围", nullable=False, server_default=sa.text("'SELF'")
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
            "uq_sys_role_code",
            sa.text("lower(role_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "后台角色"},
    )


class SysUserRole(Base):
    """sys_user_role — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_user_role"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="业务用户 ID", nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_role.id"), comment="角色 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint("user_id", "role_id", name="sys_user_role_pkey"),
        {"comment": "后台用户与角色关联"},
    )


class SysRoleInheritance(Base):
    """sys_role_inheritance — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_role_inheritance"

    parent_role_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_role.id"), comment="父角色 ID", nullable=False
    )
    child_role_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_role.id"), comment="子角色 ID", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.PrimaryKeyConstraint(
            "parent_role_id", "child_role_id", name="sys_role_inheritance_pkey"
        ),
        sa.CheckConstraint("parent_role_id<>child_role_id", name="sys_role_inheritance_check"),
        {"comment": "后台角色继承关系"},
    )


class SysRoleDataScope(Base):
    """sys_role_data_scope — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_role_data_scope"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    role_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_role.id"), comment="角色 ID", nullable=True
    )
    scope_type: Mapped[str] = mapped_column(sa.String(32), comment="数据范围类型", nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_department.id"), comment="所属部门 ID", nullable=True
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

    __table_args__ = ({"comment": "后台角色数据范围"},)
