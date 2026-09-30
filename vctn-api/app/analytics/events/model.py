"""app.analytics.events — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  behavior_event, behavior_identity_merge
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class BehaviorEvent(Base):
    """behavior_event — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_event"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    event_id: Mapped[str] = mapped_column(sa.String(128), comment="事件唯一 ID", nullable=False)
    event_code: Mapped[str] = mapped_column(sa.String(128), comment="事件编码", nullable=False)
    event_name: Mapped[str | None] = mapped_column(
        sa.String(255), comment="事件名称", nullable=True
    )
    anonymous_id_hash: Mapped[str | None] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=True
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    session_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="会话 ID（业务侧自维护，无外键）", nullable=True
    )
    platform: Mapped[str | None] = mapped_column(sa.String(32), comment="平台", nullable=True)
    device_type: Mapped[str | None] = mapped_column(
        sa.String(32), comment="设备类型", nullable=True
    )
    os: Mapped[str | None] = mapped_column(sa.String(64), comment="操作系统", nullable=True)
    browser: Mapped[str | None] = mapped_column(sa.String(128), comment="浏览器", nullable=True)
    app_code: Mapped[str | None] = mapped_column(sa.String(64), comment="应用编码", nullable=True)
    app_version: Mapped[str | None] = mapped_column(
        sa.String(64), comment="应用版本", nullable=True
    )
    page_code: Mapped[str | None] = mapped_column(sa.String(128), comment="页面编码", nullable=True)
    page_url: Mapped[str | None] = mapped_column(sa.Text, comment="页面地址", nullable=True)
    referrer: Mapped[str | None] = mapped_column(sa.Text, comment="来源页地址", nullable=True)
    module: Mapped[str | None] = mapped_column(sa.String(64), comment="所属模块", nullable=True)
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(64), comment="资源类型", nullable=True
    )
    resource_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="资源 ID", nullable=True
    )
    properties: Mapped[Any] = mapped_column(JSONB, comment="事件属性（JSONB）", nullable=True)
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="链路追踪 ID", nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(sa.String(128), comment="请求 ID", nullable=True)
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), comment="事件发生时间（UTC）", nullable=False
    )
    received_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="服务端接收时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint("event_id", name="behavior_event_event_id_key"),
        sa.Index("idx_behavior_event_code_time", "event_code", sa.text("occurred_at DESC")),
        sa.Index("idx_behavior_event_user_time", "user_id", sa.text("occurred_at DESC")),
        {"comment": "埋点行为事件"},
    )


class BehaviorIdentityMerge(Base):
    """behavior_identity_merge — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "behavior_identity_merge"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    anonymous_id_hash: Mapped[str] = mapped_column(
        sa.String(128), comment="匿名访客标识哈希", nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("biz_user.id"), comment="业务用户 ID", nullable=True
    )
    first_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="首次出现时间（UTC）", nullable=True
    )
    merged_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="合并时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "anonymous_id_hash",
            "user_id",
            name="behavior_identity_merge_anonymous_id_hash_user_id_key",
        ),
        {"comment": "匿名身份与用户合并记录"},
    )
