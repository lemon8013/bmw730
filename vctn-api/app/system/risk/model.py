"""app.system.risk — ORM models.

Generated from the frozen DDL baseline
(aicoding/sql/vctn-enterprise-ddl-v2.0.sql). Column types, nullability,
defaults, constraints and indexes are reproduced verbatim; do not edit by
hand without updating the DDL and the migration.

Tables:  risk_rule
"""

from __future__ import annotations

import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class RiskRule(Base):
    """risk_rule — ORM model generated from the frozen DDL baseline."""

    __tablename__ = "risk_rule"

    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        comment="主键 ID（雪花算法生成）",
        default=new_id,
        primary_key=True,
        autoincrement=False,
    )
    rule_code: Mapped[str] = mapped_column(sa.String(128), comment="规则编码", nullable=False)
    rule_name: Mapped[str] = mapped_column(sa.String(128), comment="规则名称", nullable=False)
    rule_type: Mapped[str] = mapped_column(sa.String(64), comment="规则类型", nullable=False)
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, comment="是否启用", nullable=False, server_default=sa.true()
    )
    threshold: Mapped[int | None] = mapped_column(sa.BigInteger, comment="触发阈值", nullable=True)
    window_seconds: Mapped[int | None] = mapped_column(
        sa.Integer, comment="统计窗口（秒）", nullable=True
    )
    action: Mapped[str] = mapped_column(sa.String(64), comment="命中后的处理动作", nullable=False)
    conditions: Mapped[Any] = mapped_column(JSONB, comment="生效条件（JSONB）", nullable=True)
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
            "uq_risk_rule_code",
            sa.text("lower(rule_code)"),
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
        {"comment": "风控规则"},
    )
