"""app.admin.users — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_user
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class SysUser(Base):
    """sys_user — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    username: Mapped[str] = mapped_column(sa.String(64), comment="用户名", nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), comment="密码哈希", nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(128), comment="显示名称", nullable=False)
    email: Mapped[str | None] = mapped_column(sa.String(320), comment="邮箱", nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(32), comment="手机号", nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_department.id"), comment="所属部门 ID", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="账号状态（ACTIVE/DISABLED/LOCKED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    is_super_admin: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否超级管理员", nullable=False, server_default=sa.false()
    )
    must_change_password: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否必须修改密码", nullable=False, server_default=sa.true()
    )
    password_changed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="密码最近修改时间（UTC）", nullable=True
    )
    password_expires_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="密码过期时间（UTC）", nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(
        sa.Integer, comment="连续登录失败次数", nullable=False, server_default=sa.text("0")
    )
    locked_until: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="锁定截止时间（UTC）", nullable=True
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="最近登录时间（UTC）", nullable=True
    )
    last_login_ip: Mapped[Any] = mapped_column(INET, comment="最近登录 IP", nullable=True)
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
            "uq_sys_user_username",
            sa.text("lower(username)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "后台管理员账号"},
    )
