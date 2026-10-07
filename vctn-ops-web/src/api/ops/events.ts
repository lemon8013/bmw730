/** Operations events (`app/ops/events`). */

import { get } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { OpsEvent } from '@/types/ops'

/** Filters accepted by `GET /ops/events`. */
export interface EventFilters {
  eventType?: string
  severity?: string
  source?: string
  traceId?: string
  start?: Date | string | null
  end?: Date | string | null
}

/** `GET /ops/events` */
export function listEvents(
  page = 1,
  pageSize = 20,
  filters: EventFilters = {},
): Promise<Page<OpsEvent>> {
  return get<Page<OpsEvent>>(opsPath('/events'), {
    params: {
      page,
      page_size: pageSize,
      event_type: filters.eventType ?? undefined,
      severity: filters.severity ?? undefined,
      source: filters.source ?? undefined,
      trace_id: filters.traceId ?? undefined,
      start: toIsoDateTime(filters.start),
      end: toIsoDateTime(filters.end),
    },
  })
}

/** `GET /ops/events/{event_id}` */
export function getEvent(eventId: string): Promise<OpsEvent> {
  return get<OpsEvent>(opsPath(`/events/${encodeURIComponent(eventId)}`))
}
