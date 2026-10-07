/**
 * Alerts and alert rules (`app/ops/alerts`).
 *
 * Acknowledging and silencing have their own permissions; resolving and rule
 * management require `OPS_ALERT_MANAGE`. The backend remains the authority —
 * the console only hides what the caller cannot do.
 */

import { del, get, post, put, type DeleteResult } from '@/api/client'
import { opsPath, toIsoDateTime } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type {
  Alert,
  AlertAckRequest,
  AlertEvaluation,
  AlertResolveRequest,
  AlertRule,
  AlertRuleCreateRequest,
  AlertRuleUpdateRequest,
  AlertSilenceRequest,
} from '@/types/ops'

/** Filters accepted by `GET /ops/alerts`. */
export interface AlertFilters {
  status?: string
  severity?: string
  alertType?: string
  start?: Date | string | null
  end?: Date | string | null
}

/** `GET /ops/alerts` */
export function listAlerts(
  page = 1,
  pageSize = 20,
  filters: AlertFilters = {},
): Promise<Page<Alert>> {
  return get<Page<Alert>>(opsPath('/alerts'), {
    params: {
      page,
      page_size: pageSize,
      status: filters.status ?? undefined,
      severity: filters.severity ?? undefined,
      alert_type: filters.alertType ?? undefined,
      start: toIsoDateTime(filters.start),
      end: toIsoDateTime(filters.end),
    },
  })
}

/** `GET /ops/alerts/{alert_id}` */
export function getAlert(alertId: string): Promise<Alert> {
  return get<Alert>(opsPath(`/alerts/${encodeURIComponent(alertId)}`))
}

/** `POST /ops/alerts/{alert_id}/ack` — requires `OPS_ALERT_ACK`. */
export function acknowledgeAlert(alertId: string, payload: AlertAckRequest): Promise<Alert> {
  return post<Alert>(opsPath(`/alerts/${encodeURIComponent(alertId)}/ack`), payload)
}

/** `POST /ops/alerts/{alert_id}/silence` — requires `OPS_ALERT_SILENCE`. */
export function silenceAlert(alertId: string, payload: AlertSilenceRequest): Promise<Alert> {
  return post<Alert>(opsPath(`/alerts/${encodeURIComponent(alertId)}/silence`), payload)
}

/** `POST /ops/alerts/{alert_id}/resolve` — requires `OPS_ALERT_MANAGE`. */
export function resolveAlert(alertId: string, payload: AlertResolveRequest): Promise<Alert> {
  return post<Alert>(opsPath(`/alerts/${encodeURIComponent(alertId)}/resolve`), payload)
}

/** `POST /ops/alerts/evaluate` — requires `OPS_ALERT_MANAGE`. */
export function evaluateAlerts(): Promise<AlertEvaluation> {
  return post<AlertEvaluation>(opsPath('/alerts/evaluate'), undefined)
}

/** Filters accepted by `GET /ops/alert-rules`. */
export interface AlertRuleFilters {
  keyword?: string
  alertType?: string
  enabled?: boolean
}

/** `GET /ops/alert-rules` */
export function listAlertRules(
  page = 1,
  pageSize = 20,
  filters: AlertRuleFilters = {},
): Promise<Page<AlertRule>> {
  return get<Page<AlertRule>>(opsPath('/alert-rules'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      alert_type: filters.alertType ?? undefined,
      enabled: filters.enabled ?? undefined,
    },
  })
}

/** `POST /ops/alert-rules` — requires `OPS_ALERT_MANAGE`. */
export function createAlertRule(payload: AlertRuleCreateRequest): Promise<AlertRule> {
  return post<AlertRule>(opsPath('/alert-rules'), payload)
}

/** `PUT /ops/alert-rules/{rule_id}` — requires `OPS_ALERT_MANAGE`. */
export function updateAlertRule(ruleId: string, payload: AlertRuleUpdateRequest): Promise<AlertRule> {
  return put<AlertRule>(opsPath(`/alert-rules/${encodeURIComponent(ruleId)}`), payload)
}

/** `DELETE /ops/alert-rules/{rule_id}` — requires `OPS_ALERT_MANAGE`. */
export function deleteAlertRule(ruleId: string): Promise<DeleteResult> {
  return del<DeleteResult>(opsPath(`/alert-rules/${encodeURIComponent(ruleId)}`))
}
