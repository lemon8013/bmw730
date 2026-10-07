"""app.ops.notifications — ORM models.

Notification channels are dispatched through a Provider registry, never through
``if channel == ...`` branches. V1 ships the Webhook provider only
(OPS-DECISION-009); adding a channel means adding a provider, not editing
business code.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsNotificationChannel(Base):
    """ops_notification_channel — a delivery channel configuration."""

    __tablename__ = "ops_notification_channel"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    channel_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="渠道编码")
    channel_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="渠道名称")
    channel_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'WEBHOOK'"),
        comment="渠道类型（WEBHOOK/EMAIL/WECOM/DINGTALK/FEISHU/SMS）",
    )
    config: Mapped[dict] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=False,
        comment="渠道配置（不含明文凭据）",
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="更新时间（UTC）"
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint("channel_code", name="uq_ops_notification_channel_code"),
        {"comment": "运维通知渠道"},
    )


class OpsNotificationGroup(Base):
    """ops_notification_group — a named bundle of channels and receivers."""

    __tablename__ = "ops_notification_group"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    group_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="通知组编码")
    group_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="通知组名称")
    channel_codes: Mapped[list] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=False,
        comment="渠道编码列表",
    )
    receivers: Mapped[list] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=False,
        comment="接收方列表",
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="更新时间（UTC）"
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="软删除时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint("group_code", name="uq_ops_notification_group_code"),
        {"comment": "运维通知组"},
    )
