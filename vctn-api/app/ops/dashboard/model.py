"""app.ops.dashboard — ORM models.

Dashboards and their widgets. Widget types are a frozen enumeration so the
frontend can render a widget without guessing; the layout model is an explicit
grid (``position_x/y`` plus ``width``/``height``) rather than free-form JSON.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsDashboard(Base):
    """ops_dashboard — a dashboard."""

    __tablename__ = "ops_dashboard"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    dashboard_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="仪表盘编码")
    name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="仪表盘名称")
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True, comment="描述说明"
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false"), comment="是否默认仪表盘"
    )
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="创建人")
    created_by_username: Mapped[str | None] = mapped_column(sa.String(64), nullable=True,
        comment="创建人账号")
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
        sa.UniqueConstraint("dashboard_code", name="uq_ops_dashboard_code"),
        {"comment": "运维仪表盘"},
    )


class OpsDashboardWidget(Base):
    """ops_dashboard_widget — one widget on one dashboard."""

    __tablename__ = "ops_dashboard_widget"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    dashboard_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_dashboard.id"), nullable=False, comment="所属仪表盘"
    )
    widget_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False,
        comment="组件类型（STAT/LINE/AREA/BAR/TABLE/GAUGE/TOPN/TIMELINE）",
    )
    title: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="组件标题")
    metric_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, comment="指标键")
    options: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="组件渲染选项",
    )
    position_x: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="栅格列位置"
    )
    position_y: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="栅格行位置"
    )
    width: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("6"), comment="栅格宽度"
    )
    height: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("4"), comment="栅格高度"
    )
    sort_order: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="排序序号"
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
        sa.Index("ix_ops_dashboard_widget_dashboard", "dashboard_id"),
        {"comment": "运维仪表盘组件"},
    )
