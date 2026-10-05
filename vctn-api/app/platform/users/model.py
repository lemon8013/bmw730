"""app.platform.users — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  biz_user, biz_user_profile, biz_user_login_identity, biz_user_password_history,
    biz_user_verification, biz_user_session, biz_user_login_log
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class BizUser(Base):
    """biz_user — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    username: Mapped[str | None] = mapped_column(sa.String(64), comment="用户名", nullable=True)
    nickname: Mapped[str] = mapped_column(sa.String(128), comment="昵称", nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="账号状态（ACTIVE/DISABLED/BANNED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    email: Mapped[str | None] = mapped_column(sa.String(320), comment="邮箱", nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(32), comment="手机号", nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.Text, comment="头像地址", nullable=True)
    registered_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="注册时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="最近登录时间（UTC）", nullable=True
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
            "uq_biz_user_username",
            sa.text("lower(username)"),
            unique=True,
            postgresql_where=sa.text("username IS NOT NULL AND deleted_at IS NULL"),
        ),
        {"comment": "业务用户账号"},
    )


class BizUserProfile(Base):
    """biz_user_profile — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_profile"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("biz_user.id"),
        comment="业务用户 ID（同时作为主键）",
        primary_key=True,
        autoincrement=False,
    )
    gender: Mapped[str | None] = mapped_column(sa.String(16), comment="性别", nullable=True)
    birthday: Mapped[datetime.date | None] = mapped_column(sa.Date, comment="生日", nullable=True)
    bio: Mapped[str | None] = mapped_column(sa.String(1000), comment="个人简介", nullable=True)
    timezone: Mapped[str | None] = mapped_column(sa.String(64), comment="时区", nullable=True)
    locale: Mapped[str | None] = mapped_column(sa.String(32), comment="语言区域", nullable=True)
    preferences: Mapped[Any] = mapped_column(JSONB, comment="用户偏好（JSONB）", nullable=True)
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

    __table_args__ = ({"comment": "业务用户资料"},)


class BizUserLoginIdentity(Base):
    """biz_user_login_identity — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_login_identity"

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
    identity_type: Mapped[str] = mapped_column(sa.String(32), comment="身份类型", nullable=False)
    identity_value: Mapped[str] = mapped_column(sa.String(255), comment="身份值", nullable=False)
    verified: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否已验证", nullable=False, server_default=sa.false()
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
        sa.UniqueConstraint(
            "identity_type",
            "identity_value",
            name="biz_user_login_identity_identity_type_identity_value_key",
        ),
        {"comment": "业务用户登录身份"},
    )


class BizUserPasswordHistory(Base):
    """biz_user_password_history — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_password_history"

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
    password_hash: Mapped[str] = mapped_column(sa.String(255), comment="密码哈希", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "业务用户密码历史"},)


class BizUserVerification(Base):
    """biz_user_verification — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_verification"

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
    verification_type: Mapped[str] = mapped_column(
        sa.String(32), comment="验证类型", nullable=False
    )
    target_hash: Mapped[str | None] = mapped_column(
        sa.String(255), comment="验证目标哈希", nullable=True
    )
    code_hash: Mapped[str | None] = mapped_column(
        sa.String(255), comment="验证码哈希", nullable=True
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), comment="过期时间（UTC）", nullable=False
    )
    consumed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="消费时间（UTC）", nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(
        sa.Integer, comment="已尝试次数", nullable=False, server_default=sa.text("0")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "业务用户验证码"},)


class BizUserSession(Base):
    """biz_user_session — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_session"

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
    refresh_token_hash: Mapped[str | None] = mapped_column(
        sa.String(255), comment="刷新令牌哈希", nullable=True
    )
    session_status: Mapped[str] = mapped_column(
        sa.String(16), comment="会话状态", nullable=False, server_default=sa.text("'ACTIVE'")
    )
    anonymous_id_hash: Mapped[str | None] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=True
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

    __table_args__ = ({"comment": "业务用户登录会话"},)


class BizUserLoginLog(Base):
    """biz_user_login_log — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "biz_user_login_log"

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
    identity_type: Mapped[str | None] = mapped_column(
        sa.String(32), comment="身份类型", nullable=True
    )
    success: Mapped[bool] = mapped_column(sa.Boolean, comment="是否成功", nullable=False)
    failure_code: Mapped[str | None] = mapped_column(
        sa.String(64), comment="失败原因编码", nullable=True
    )
    ip: Mapped[Any] = mapped_column(INET, comment="IP 地址", nullable=True)
    user_agent: Mapped[str | None] = mapped_column(
        sa.Text, comment="客户端 User-Agent", nullable=True
    )
    anonymous_id_hash: Mapped[str | None] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=True
    )
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="事件发生时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = ({"comment": "业务用户登录日志"},)
