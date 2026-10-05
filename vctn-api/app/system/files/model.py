"""app.system.files — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  sys_file, sys_export_job
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class SysFile(Base):
    """sys_file — ORM model generated from the frozen DDL baseline.

    The DDL column ``metadata`` keeps its exact name; the Python
    attribute is ``metadata_payload`` because SQLAlchemy reserves ``metadata``.
    """

    __tablename__ = "sys_file"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    owner_type: Mapped[str | None] = mapped_column(
        sa.String(32), comment="归属对象类型", nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="归属对象 ID", nullable=True
    )
    storage_provider: Mapped[str] = mapped_column(
        sa.String(32), comment="存储服务提供方", nullable=False
    )
    bucket: Mapped[str | None] = mapped_column(sa.String(255), comment="存储桶", nullable=True)
    object_key: Mapped[str] = mapped_column(sa.String(1024), comment="对象键", nullable=False)
    original_name: Mapped[str | None] = mapped_column(
        sa.String(255), comment="原始文件名", nullable=True
    )
    content_type: Mapped[str | None] = mapped_column(
        sa.String(255), comment="内容类型", nullable=True
    )
    size_bytes: Mapped[int | None] = mapped_column(
        sa.BigInteger, comment="文件大小（字节）", nullable=True
    )
    checksum: Mapped[str | None] = mapped_column(
        sa.String(128), comment="文件校验和", nullable=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(32),
        comment="文件状态（ACTIVE/DELETED）",
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )
    metadata_payload: Mapped[Any] = mapped_column(
        "metadata", JSONB, comment="扩展元数据（JSONB）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="软删除时间（UTC，NULL 表示未删除）", nullable=True
    )

    __table_args__ = (
        sa.Index("uq_sys_file_object", "storage_provider", "bucket", "object_key", unique=True),
        {"comment": "文件对象"},
    )


class SysExportJob(Base):
    """sys_export_job — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "sys_export_job"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    requested_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("sys_user.id"),
        comment="申请人 ID（后台管理员）",
        nullable=True,
    )
    export_type: Mapped[str] = mapped_column(sa.String(64), comment="导出类型", nullable=False)
    filter_json: Mapped[Any] = mapped_column(JSONB, comment="导出筛选条件（JSONB）", nullable=True)
    status: Mapped[str] = mapped_column(
        sa.String(32), comment="状态", nullable=False, server_default=sa.text("'PENDING'")
    )
    file_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("sys_file.id"), comment="导出结果文件 ID", nullable=True
    )
    row_count: Mapped[int | None] = mapped_column(sa.BigInteger, comment="导出行数", nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, comment="错误信息", nullable=True)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="过期时间（UTC）", nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        comment="创建时间（UTC）",
        nullable=False,
        server_default=sa.func.now(),
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="开始执行时间（UTC）", nullable=True
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), comment="结束执行时间（UTC）", nullable=True
    )

    __table_args__ = ({"comment": "数据导出任务"},)
