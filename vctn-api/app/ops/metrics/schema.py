"""app.ops.metrics — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class MetricDefinitionResponse(ApiModel):
    """A metric definition."""

    id: StringId
    metric_key: str
    metric_name: str
    metric_type: str
    unit: str | None = None
    description: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class MetricSampleCreateRequest(ApiModel):
    """One metric sample collected by an agent or collector."""

    metric_key: str
    host_id: str | None = None
    service_id: str | None = None
    endpoint_id: str | None = None
    environment: str = "PRODUCTION"
    value: float
    labels: dict | None = None
    collected_at: datetime.datetime


class MetricSamplesCreateRequest(ApiModel):
    """A batch of metric samples."""

    samples: list[MetricSampleCreateRequest]


class MetricSamplesCreateResponse(ApiModel):
    """The accepted metric sample identifiers."""

    accepted: int
    sample_ids: list[StringId]


class MetricSeriesPoint(ApiModel):
    """One time-series point."""

    timestamp: datetime.datetime
    value: float
    min_value: float
    max_value: float
    sum_value: float
    sample_count: int
