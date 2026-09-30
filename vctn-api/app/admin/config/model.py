"""app.admin.config — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_config, sys_feature_flag
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysConfig(Base):
    """sys_config — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_config"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    config_key: Mapped[str] = mapped_column(sa.String(255), comment="配置键", nullable=False)
    config_name: Mapped[str] = mapped_column(sa.String(128), comment="配置名称", nullable=False)
    config_group: Mapped[str] = mapped_column(sa.String(64), comment="配置分组", nullable=False)
    value_type: Mapped[str] = mapped_column(sa.String(32), comment="值类型", nullable=False)
    config_value: Mapped[str | None] = mapped_column(sa.Text, comment="配置值", nullable=True)
    default_value: Mapped[str | None] = mapped_column(sa.Text, comment="默认值", nullable=True)
    editable: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否允许在线编辑", nullable=False, server_default=sa.true()
    )
    requires_restart: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否需要重启生效", nullable=False, server_default=sa.false()
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="配置状态（ACTIVE/DISABLED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    version: Mapped[int] = mapped_column(
        sa.BigInteger, comment="乐观锁版本号", nullable=False, server_default=sa.text("1")
    )
    effective_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="生效时间（UTC）", nullable=True
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
            "uq_sys_config_key",
            sa.text("lower(config_key)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "系统配置项"},
    )


class SysFeatureFlag(Base):
    """sys_feature_flag — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_feature_flag"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    flag_key: Mapped[str] = mapped_column(sa.String(128), comment="开关键", nullable=False)
    flag_name: Mapped[str] = mapped_column(sa.String(128), comment="开关名称", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.false()
    )
    strategy: Mapped[str] = mapped_column(
        sa.String(32), comment="灰度策略", nullable=False, server_default=sa.text("'GLOBAL'")
    )
    percentage: Mapped[int | None] = mapped_column(
        sa.Integer, comment="放量百分比（0-100）", nullable=True
    )
    conditions: Mapped[Any] = mapped_column(JSONB, comment="生效条件（JSONB）", nullable=True)
    description: Mapped[str | None] = mapped_column(
        sa.String(500), comment="描述说明", nullable=True
    )
    version: Mapped[int] = mapped_column(
        sa.BigInteger, comment="乐观锁版本号", nullable=False, server_default=sa.text("1")
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
        sa.CheckConstraint(
            "percentage IS NULL OR percentage BETWEEN 0 AND 100",
            name="sys_feature_flag_percentage_check",
        ),
        sa.Index(
            "uq_sys_feature_flag_key",
            sa.text("lower(flag_key)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "功能开关"},
    )
