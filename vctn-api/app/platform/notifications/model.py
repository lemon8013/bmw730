"""app.platform.notifications — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_notification
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysNotification(Base):
    """sys_notification — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_notification"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    user_type: Mapped[str] = mapped_column(sa.String(32), comment="接收者类型", nullable=False)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="接收者用户 ID（配合 user_type 区分后台管理员与业务用户）",
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(
        sa.String(64), comment="通知类型", nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(255), comment="标题", nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, comment="内容", nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, comment="业务载荷（JSONB）", nullable=True)
    read_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="读取时间（UTC）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("idx_notification_user_time", "user_type", "user_id", sa.text("created_at DESC")),
        {"comment": "站内通知"},
    )
