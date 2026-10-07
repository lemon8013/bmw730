"""app.ops.metrics — ORM models.

Metric definitions, raw samples and rollups.

Storage decision (OPS-DECISION-001): plain PostgreSQL tables. Rollups are
written by the aggregation task so a long range query reads the hourly/daily
rows instead of scanning raw samples.

Retention decision (OPS-DECISION-007): raw samples 7 days, hourly 30 days,
daily 180 days. The numbers live in ``Settings`` and are never hard coded in a
query.
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.ids import new_id


class OpsMonitor(Base):
    """ops_monitor — the unified monitoring target registry."""

    __tablename__ = "ops_monitor"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    monitor_code: Mapped[str] = mapped_column(sa.String(64), nullable=False, comment="监控对象编码")
    monitor_name: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, comment="监控对象名称"
    )
    monitor_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False,
        comment="监控类型（HOST/SERVICE/API/DATABASE/REDIS/AVAILABILITY/JOB）",
    )
    target_type: Mapped[str] = mapped_column(sa.String(32), nullable=False, comment="目标对象类型")
    target_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="目标对象 ID"
    )
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true"), comment="是否启用"
    )
    metadata_payload: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
        comment="结构化扩展属性",
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
        sa.UniqueConstraint("monitor_code", name="uq_ops_monitor_code"),
        sa.Index("ix_ops_monitor_type", "monitor_type"),
        {"comment": "运维监控对象"},
    )


class OpsMetricDefinition(Base):
    """ops_metric_definition — a metric key and its semantics."""

    __tablename__ = "ops_metric_definition"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    metric_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="指标键")
    metric_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="指标名称")
    metric_type: Mapped[str] = mapped_column(
        sa.String(32), nullable=False,
        comment="指标类型（counter/gauge/rate/latency/availability）",
    )
    unit: Mapped[str | None] = mapped_column(sa.String(32), nullable=True, comment="单位")
    description: Mapped[str | None] = mapped_column(
        sa.String(500), nullable=True, comment="描述说明"
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
        sa.UniqueConstraint("metric_key", name="uq_ops_metric_definition_key"),
        {"comment": "运维指标定义"},
    )


class OpsMetricSample(Base):
    """ops_metric_sample — one raw metric point."""

    __tablename__ = "ops_metric_sample"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    metric_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="指标键")
    host_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="关联主机")
    service_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True, comment="关联服务")
    endpoint_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, nullable=True, comment="关联端点"
    )
    environment: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default=sa.text("'PRODUCTION'"), comment="所属环境"
    )
    value: Mapped[float] = mapped_column(sa.Float, nullable=False, comment="指标值")
    labels: Mapped[dict | None] = mapped_column(
        sa.JSON().with_variant(sa.dialects.postgresql.JSONB, "postgresql"), nullable=True,
            comment="维度标签"
    )
    collected_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="采集时间（UTC）"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.Index("ix_ops_metric_sample_key_collected", "metric_key", "collected_at"),
        sa.Index("ix_ops_metric_sample_collected", "collected_at"),
        {"comment": "运维指标原始采样"},
    )


class OpsMetricHourly(Base):
    """ops_metric_hourly — hourly rollup of :class:`OpsMetricSample`."""

    __tablename__ = "ops_metric_hourly"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    metric_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="指标键")
    dimension_key: Mapped[str] = mapped_column(sa.String(255), nullable=False, comment="维度键")
    bucket_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="聚合时间桶（UTC，整点）"
    )
    avg_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="平均值")
    min_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="最小值")
    max_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="最大值")
    sum_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="求和值")
    sample_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="采样数量"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "metric_key", "dimension_key", "bucket_at", name="uq_ops_metric_hourly_bucket"
        ),
        sa.Index("ix_ops_metric_hourly_bucket", "bucket_at"),
        {"comment": "运维指标小时聚合"},
    )


class OpsMetricDaily(Base):
    """ops_metric_daily — daily rollup of :class:`OpsMetricSample`."""

    __tablename__ = "ops_metric_daily"

    id: Mapped[int] = mapped_column(
        sa.BigInteger, primary_key=True, default=new_id, autoincrement=False,
        comment="主键 ID（雪花算法生成）",
    )
    metric_key: Mapped[str] = mapped_column(sa.String(128), nullable=False, comment="指标键")
    dimension_key: Mapped[str] = mapped_column(sa.String(255), nullable=False, comment="维度键")
    bucket_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, comment="聚合时间桶（UTC，零点）"
    )
    avg_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="平均值")
    min_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="最小值")
    max_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="最大值")
    sum_value: Mapped[float | None] = mapped_column(sa.Float, nullable=True, comment="求和值")
    sample_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0"), comment="采样数量"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(),
            comment="创建时间（UTC）"
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "metric_key", "dimension_key", "bucket_at", name="uq_ops_metric_daily_bucket"
        ),
        sa.Index("ix_ops_metric_daily_bucket", "bucket_at"),
        {"comment": "运维指标天聚合"},
    )
