/** Metric definitions and their time series (`app/ops/metrics`). */

import { get, post } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { MetricDefinition, MetricSeriesPoint } from '@/types/ops'

/** A sample accepted by the collector write endpoint. */
export interface MetricSampleInput {
  metric_key: string
  host_id?: string | null
  service_id?: string | null
  endpoint_id?: string | null
  environment?: string
  value: number
  labels?: Record<string, unknown> | null
  collected_at: string
}

export interface MetricSamplesCreateResult {
  accepted: number
  sample_ids: string[]
}

/** `GET /ops/metrics` */
export function listMetrics(
  page = 1,
  pageSize = 20,
  keyword?: string,
  metricType?: string,
): Promise<Page<MetricDefinition>> {
  return get<Page<MetricDefinition>>(opsPath('/metrics'), {
    params: {
      page,
      page_size: pageSize,
      keyword: keyword ?? undefined,
      metric_type: metricType ?? undefined,
    },
  })
}

/** Filters accepted by `GET /ops/metrics/series`. */
export interface SeriesQuery {
  metricKey: string
  start: Date | string
  end: Date | string
  step: string
  hostId?: string | null
  serviceId?: string | null
  endpointId?: string | null
}

/**
 * `GET /ops/metrics/series`
 *
 * `start`, `end` and `step` are all mandatory on the backend: the window is the
 * caller's decision, never a server default.
 */
export function fetchMetricSeries(query: SeriesQuery): Promise<MetricSeriesPoint[]> {
  return get<MetricSeriesPoint[]>(opsPath('/metrics/series'), {
    params: {
      metric_key: query.metricKey,
      start: toIsoDateTime(query.start),
      end: toIsoDateTime(query.end),
      step: query.step,
      host_id: query.hostId ?? undefined,
      service_id: query.serviceId ?? undefined,
      endpoint_id: query.endpointId ?? undefined,
    },
  })
}

/** `POST /ops/metrics/samples` — requires `OPS_MONITOR_MANAGE`. */
export function createMetricSamples(
  samples: readonly MetricSampleInput[],
): Promise<MetricSamplesCreateResult> {
  return post<MetricSamplesCreateResult>(opsPath('/metrics/samples'), { samples: [...samples] })
}
