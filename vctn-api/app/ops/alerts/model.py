"""app.ops.alerts — ORM models.

Alert rules, alert instances, status history and notification records.

Lifecycle: ``NORMAL -> TRIGGERED -> FIRING -> ACKNOWLEDGED -> RESOLVED``.
Silencing is a separate dimension: it suppresses notification only and never
resolves an alert.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsAlertRule(Base):
    """ops_alert_rule — a configurable threshold rule."""

    __tablename__ = "ops_alert_rule"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    rule_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="规则编码")
    rule_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="规则名称")
    alert_type: Mapped[str] = mapped_column(
        sa.String(64), nullable=False,
        comment="告警类型（CPU_HIGH/MEMORY_HIGH/SERVICE_DOWN/API_ERROR_RATE_HIGH/...）",
    )
    metric_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="监控指标键")
    condition: Mapped[str] = mapped_column(
        sa.String(16), nullable=False, server_default=sa.text("'GT'"),
        comment="比较条件（GT/GTE/LT/LTE/EQ/NE）",
    )
    threshold: Mapped[float] = mapped_column(
        sa.Float, nullable=False, comment="阈值（配置化，不允许硬编码）"
    )
    duration_seconds: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("300"), comment="持续时长（秒）"
    )
    severity: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'WARNING'"),
        comment="严重级别（INFO/WARNING/ERROR/CRITICAL）",
    )
    scope_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'GLOBAL'"),
        comment="作用范围类型（GLOBAL/HOST/SERVICE/ENDPOINT）",
    )
    scope_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="作用范围对象 ID"
    )
    notification_policy: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="通知策略（渠道编码列表与静默配置）",
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
        sa.UniqueConstraint("rule_code", name="uq_ops_alert_rule_code"),
        sa.Index("ix_ops_alert_rule_type", "alert_type"),
        {"comment": "运维告警规则"},
    )


class OpsAlert(Base):
    """ops_alert — one alert instance, deduplicated by ``fingerprint``."""

    __tablename__ = "ops_alert"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    fingerprint: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="去重指纹")
    rule_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_alert_rule.id"), nullable=True, comment="命中规则"
    )
    alert_type: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="告警类型")
    severity: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'WARNING'"), comment="严重级别"
    )
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'TRIGGERED'"),
        comment="告警状态（TRIGGERED/FIRING/ACKNOWLEDGED/RESOLVED）",
    )
    resource_type: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="资源类型"
    )
    resource_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="资源 ID")
    host_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="关联主机")
    service_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_service.id"), nullable=True, comment="关联服务"
    )
    metric_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, comment="指标键")
    metric_value: Mapped[float | None] = mapped_column(
        sa.Float, nullable=True, comment="触发时指标值"
    )
    threshold: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="触发阈值")
    description: Mapped[str | None] = mapped_column(
        sa.String(1000), nullable=True, comment="告警描述"
    )
    trace_id: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True, comment="链路追踪 ID"
    )
    triggered_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="触发时间（UTC）"
    )
    acknowledged_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="确认时间（UTC）"
    )
    acknowledged_by: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="确认人"
    )
    silenced_until: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="静默截止时间（UTC）"
    )
    silence_reason: Mapped[str | None] = mapped_column(sa.String(500), nullable=True,
        comment="静默原因")
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="恢复时间（UTC）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="更新时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint("fingerprint", name="uq_ops_alert_fingerprint"),
        sa.Index("ix_ops_alert_status_severity", "status", "severity"),
        sa.Index("ix_ops_alert_triggered", "triggered_at"),
        {"comment": "运维告警"},
    )


class OpsAlertHistory(Base):
    """ops_alert_history — append-only status transitions of an alert."""

    __tablename__ = "ops_alert_history"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    alert_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_alert.id"), nullable=False, comment="所属告警"
    )
    from_status: Mapped[str | None] = mapped_column(sa.String(32), nullable=True, comment="原状态")
    to_status: Mapped[str] = mapped_column(sa.String(32), nullable=False, comment="新状态")
    actor_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="操作人")
    actor_username: Mapped[str | None] = mapped_column(sa.String(64), nullable=True,
        comment="操作人账号")
    note: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True, comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_alert_history_alert", "alert_id", "created_at"),
        {"comment": "运维告警状态历史"},
    )


class OpsAlertNotification(Base):
    """ops_alert_notification — one delivery attempt for one alert."""

    __tablename__ = "ops_alert_notification"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    alert_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("ops_alert.id"), nullable=False, comment="所属告警"
    )
    channel_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("ops_notification_channel.id"),
        nullable=True,
        comment="通知渠道",
    )
    channel_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="渠道编码")
    receiver: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, comment="接收方")
    status: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PENDING'"),
        comment="发送状态（PENDING/SENT/FAILED/SKIPPED）",
    )
    retry_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="重试次数"
    )
    sent_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, comment="发送时间（UTC）"
    )
    error_message: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True,
        comment="错误信息")
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="更新时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_alert_notification_alert", "alert_id"),
        sa.Index("ix_ops_alert_notification_status", "status"),
        {"comment": "运维告警通知记录"},
    )
