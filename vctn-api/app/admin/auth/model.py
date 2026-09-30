"""app.admin.auth — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_session, sys_mfa_factor, sys_password_history
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysSession(Base):
    """sys_session — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_session"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="后台管理员用户 ID", nullable=True
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(
        sa.String(255), comment="刷新令牌哈希", nullable=True
    )
    session_status: Mapped[str] = mapped_column(
        sa.String(16), comment="会话状态", nullable=False, server_default=sa.text("'ACTIVE'")
    )
    ip: Mapped[Any] = mapped_column(INET, comment="IP 地址", nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text, comment="客户端 User-Agent", nullable=True
    )
    device_type: Mapped[str | None] = mapped_column(
        sa.String(32), comment="设备类型", nullable=True
    )
    login_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="登录时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    last_active_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="最近活跃时间（UTC）", nullable=True
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), comment="过期时间（UTC）", nullable=False
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="吊销时间（UTC）", nullable=True
    )
    revoke_reason: Mapped[str | None] = mapped_column(
        sa.String(255), comment="吊销原因", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_sys_session_user", "user_id"),
        {"comment": "后台登录会话"},
    )


class SysMfaFactor(Base):
    """sys_mfa_factor — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_mfa_factor"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="后台管理员用户 ID", nullable=True
    )
    factor_type: Mapped[str] = mapped_column(sa.String(32), comment="因子类型", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16), comment="状态", nullable=False, server_default=sa.text("'ACTIVE'")
    )
    secret_ciphertext: Mapped[str | None] = mapped_column(
        sa.Text, comment="MFA 密钥密文", nullable=True
    )
    verified_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="验证通过时间（UTC）", nullable=True
    )
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="最近使用时间（UTC）", nullable=True
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

    __table_args__ = ({"comment": "后台多因素认证因子"},)


class SysPasswordHistory(Base):
    """sys_password_history — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_password_history"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_user.id"), comment="后台管理员用户 ID", nullable=True
    )
    password_hash: Mapped[str] = mapped_column(sa.String(255), comment="密码哈希", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "后台密码历史"},)
