"""app.admin.export — ORM model.

The export task records the lifecycle of an administrative export job. No new
business table is introduced elsewhere: this is the single new table owned by
the admin management layer.

Table:  sys_export_task
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SysExportTask(Base):
    """sys_export_task — administrative export job record."""

    __tablename__ = "sys_export_task"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, comment="主键 ID（雪花算法生成）", primary_key=True, autoincrement=False
    )
    task_type: Mapped[str] = mapped_column(
        sa.String(64), comment="导出类型（如 LOG_AUDIT / NOTIFICATION 等）", nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        comment="状态：PENDING/PROCESSING/SUCCESS/FAILED",
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    file_id: Mapped[str | None] = mapped_column(
        sa.String(128), comment="生成文件 ID（成功后填充）", nullable=True
    )
    requested_by: Mapped[int] = mapped_column(
        sa.BigInteger, comment="发起管理员 ID", nullable=False
    )
    progress: Mapped[int] = mapped_column(
        sa.Integer, comment="进度百分比 0-100", nullable=False, server_default=sa.text("0")
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text, comment="失败原因（FAILED 时填充）", nullable=True
    )
    params: Mapped[Any] = mapped_column(
        JSONB, comment="导出参数快照（JSONB）", nullable=True
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
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="完成时间（UTC，NULL 表示未完成）", nullable=True
    )

    __table_args__ = ({"comment": "后台导出任务"},)
