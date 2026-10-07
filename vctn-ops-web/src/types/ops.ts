/**
 * Operations domain types.
 *
 * Mirrors `app/ops/<module>/schema.py` field by field: every name and every
 * nullability here exists in the backend contract, and nothing is invented.
 *
 * Two rules run through the whole file:
 * * identifiers are `EntityId` — the columns are BIGINT and the API serialises
 *   them as strings, so they must never be held in a `number`;
 * * every collector reading (PostgreSQL, Redis) carries the same degradation
 *   envelope, so a failed probe renders as "collection failed" and never as an
 *   HTTP error.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

/* ---------- Shared ---------- */

/** Degradation envelope shared by every collector reading. */
export interface ProbeResult {
  status: string
  collected_at: IsoDateTime
  error: string | null
}

/* ---------- dashboard ---------- */

/** One of the most recent operations events (`OverviewEventResponse`). */
export interface OverviewEvent {
  id: EntityId
  event_id: string
  event_type: string
  source: string
  severity: string
  message: string | null
  occurred_at: IsoDateTime
}

/** The operations overview (`OverviewResponse`). */
export interface OverviewResponse {
  host_count: number
  online_host_count: number
  service_count: number
  abnormal_service_count: number
  active_alert_count: number
  alerts_by_severity: Record<string, number>
  agent_online_count: number
  availability_success_rate: number
  availability_check_count: number
  availability_window_hours: number
  recent_event_limit: number
  recent_events: OverviewEvent[]
  generated_at: IsoDateTime
}

/** A widget on a dashboard (`WidgetResponse`). */
export interface Widget {
  id: EntityId
  dashboard_id: EntityId
  widget_type: string
  title: string
  metric_key: string | null
  options: Record<string, unknown> | null
  position_x: number
  position_y: number
  width: number
  height: number
  sort_order: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** A dashboard without its widgets (`DashboardResponse`). */
export interface Dashboard {
  id: EntityId
  dashboard_code: string
  name: string
  description: string | null
  is_default: boolean
  created_by: EntityId | null
  created_by_username: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** A dashboard together with its widgets (`DashboardDetailResponse`). */
export interface DashboardDetail extends Dashboard {
  widgets: Widget[]
}

export interface DashboardCreateRequest {
  dashboard_code: string
  name: string
  description?: string | null
  is_default?: boolean
}

export interface DashboardUpdateRequest {
  name?: string | null
  description?: string | null
  is_default?: boolean | null
}

export interface WidgetCreateRequest {
  widget_type: string
  title: string
  metric_key?: string | null
  options?: Record<string, unknown> | null
  position_x?: number
  position_y?: number
  width?: number
  height?: number
  sort_order?: number
}

export interface WidgetUpdateRequest {
  widget_type?: string | null
  title?: string | null
  metric_key?: string | null
  options?: Record<string, unknown> | null
  position_x?: number | null
  position_y?: number | null
  width?: number | null
  height?: number | null
  sort_order?: number | null
}

/* ---------- hosts ---------- */

export interface Host {
  id: EntityId
  hostname: string
  display_name: string | null
  ip_address: string | null
  os_type: string | null
  os_version: string | null
  cpu_cores: number | null
  memory_total_mb: number | null
  disk_total_gb: number | null
  environment: string
  host_group_id: EntityId | null
  agent_id: EntityId | null
  status: string
  last_seen_at: IsoDateTime | null
  tags: Record<string, unknown> | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface HostGroup {
  id: EntityId
  group_code: string
  group_name: string
  description: string | null
  sort_order: number
}

export interface Environment {
  id: EntityId
  env_code: string
  env_name: string
  description: string | null
  sort_order: number
}

export interface HostCreateRequest {
  hostname: string
  display_name?: string | null
  ip_address?: string | null
  os_type?: string | null
  os_version?: string | null
  cpu_cores?: number | null
  memory_total_mb?: number | null
  disk_total_gb?: number | null
  environment?: string
  host_group_id?: string | null
  tags?: Record<string, unknown> | null
}

export interface HostUpdateRequest {
  display_name?: string | null
  ip_address?: string | null
  os_type?: string | null
  os_version?: string | null
  cpu_cores?: number | null
  memory_total_mb?: number | null
  disk_total_gb?: number | null
  environment?: string | null
  host_group_id?: string | null
  status?: string | null
  tags?: Record<string, unknown> | null
}

/* ---------- services ---------- */

export interface Service {
  id: EntityId
  service_code: string
  service_name: string
  service_type: string
  environment: string
  host_id: EntityId | null
  status: string
  last_check_at: IsoDateTime | null
  availability_rate: number | null
  error_rate: number | null
  avg_latency_ms: number | null
  tags: Record<string, unknown> | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface ServiceDependency {
  id: EntityId
  service_id: EntityId
  depends_on_service_id: EntityId
  dependency_type: string
  created_at: IsoDateTime
}

export interface ServiceCreateRequest {
  service_code: string
  service_name: string
  service_type?: string
  environment?: string
  host_id?: string | null
  tags?: Record<string, unknown> | null
}

export interface ServiceUpdateRequest {
  service_name?: string | null
  service_type?: string | null
  environment?: string | null
  host_id?: string | null
  status?: string | null
  last_check_at?: IsoDateTime | null
  availability_rate?: number | null
  error_rate?: number | null
  avg_latency_ms?: number | null
  tags?: Record<string, unknown> | null
}

export interface ServiceDependencyCreateRequest {
  depends_on_service_id: string
  dependency_type?: string
}

/* ---------- apis ---------- */

export interface MonitoredEndpoint {
  id: EntityId
  endpoint_key: string
  http_method: string
  path_pattern: string
  service_id: EntityId | null
  environment: string
  is_monitored: boolean
  request_count: number
  error_count: number
  avg_latency_ms: number | null
  p95_latency_ms: number | null
  last_seen_at: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface EndpointMetrics {
  endpoint_id: EntityId
  hours: number
  window_start: IsoDateTime
  window_end: IsoDateTime
  request_count: number
  error_count: number
  error_rate: number
  avg_latency_ms: number
  p95_latency_ms: number
  sample_count: number
}

/* ---------- database ---------- */

export interface ConnectionStateCount {
  state: string
  count: number
}

export interface DatabaseOverview extends ProbeResult {
  version: string | null
  database_name: string | null
  uptime_seconds: number | null
  connection_count: number | null
  cache_hit_ratio: number | null
  database_size_bytes: number | null
}

export interface DatabaseConnections extends ProbeResult {
  total: number | null
  max_connections: number | null
  utilization_ratio: number | null
  states: ConnectionStateCount[]
}

export interface DatabaseTransactions extends ProbeResult {
  commits: number | null
  rollbacks: number | null
  deadlocks: number | null
  rollback_ratio: number | null
}

export interface WaitingSessionItem {
  pid: number
  database_name: string | null
  state: string | null
  wait_event_type: string | null
  wait_event: string | null
  wait_seconds: number | null
}

export interface DatabaseLocks extends ProbeResult {
  total_locks: number | null
  granted_locks: number | null
  waiting_locks: number | null
  waiting_sessions: WaitingSessionItem[]
}

export interface SlowStatementItem {
  query_id: string | null
  calls: number | null
  rows: number | null
  total_ms: number | null
  mean_ms: number | null
  max_ms: number | null
  statement: string | null
}

export interface LongRunningQueryItem {
  pid: number
  database_name: string | null
  wait_event_type: string | null
  wait_event: string | null
  duration_seconds: number | null
}

export interface DatabaseSlowQueries extends ProbeResult {
  statements_extension_available: boolean
  calls: number | null
  rows: number | null
  total_ms: number | null
  mean_ms: number | null
  max_ms: number | null
  slowest_statements: SlowStatementItem[]
  long_running_queries: LongRunningQueryItem[]
}

export interface TableStorageItem {
  schema_name: string
  table_name: string
  total_bytes: number | null
  heap_bytes: number | null
  index_bytes: number | null
  live_rows: number | null
}

export interface DatabaseStorage extends ProbeResult {
  database_name: string | null
  database_size_bytes: number | null
  tables: TableStorageItem[]
}

export interface DatabaseCache extends ProbeResult {
  blocks_hit: number | null
  blocks_read: number | null
  hit_ratio: number | null
}

/* ---------- redis ---------- */

export interface RedisOverview extends ProbeResult {
  version: string | null
  mode: string | null
  role: string | null
  uptime_seconds: number | null
  connected_clients: number | null
  blocked_clients: number | null
  instantaneous_ops_per_sec: number | null
  hits: number | null
  misses: number | null
  hit_ratio: number | null
  evicted_keys: number | null
  expired_keys: number | null
  used_memory_bytes: number | null
  used_memory_human: string | null
  total_keys: number | null
  slowlog_length: number | null
}

export interface RedisKeyspaceItem {
  name: string
  keys: number
  expires: number | null
  avg_ttl: number | null
}

export interface RedisKeyspace extends ProbeResult {
  databases: RedisKeyspaceItem[]
  total_keys: number
}

export interface RedisMemory extends ProbeResult {
  used_memory_bytes: number | null
  used_memory_human: string | null
  used_memory_peak_bytes: number | null
  used_memory_peak_human: string | null
  used_memory_rss_bytes: number | null
  max_memory_bytes: number | null
  max_memory_policy: string | null
  fragmentation_ratio: number | null
  utilization_ratio: number | null
}

export interface RedisClients extends ProbeResult {
  connected_clients: number | null
  blocked_clients: number | null
  max_clients: number | null
  input_buffer_bytes: number | null
  output_buffer_bytes: number | null
  utilization_ratio: number | null
}

/* ---------- logs ---------- */

export interface LogEntry {
  log_type: string
  id: EntityId
  trace_id: string | null
  request_id: string | null
  created_at: IsoDateTime
  summary: string
  level: string | null
  result: string | null
  actor_user_id: EntityId | null
  ip: string | null
  user_agent: string | null
  method: string | null
  path: string | null
  status_code: number | null
  duration_ms: number | null
  logger_name: string | null
  exception_type: string | null
  error_code: string | null
  resource_type: string | null
  resource_id: string | null
  metadata: Record<string, unknown> | null
}

export interface LogContextItem {
  log_type: string
  id: EntityId
  trace_id: string | null
  request_id: string | null
  created_at: IsoDateTime
  summary: string
  level: string | null
  result: string | null
  metadata: Record<string, unknown> | null
}

export interface LogContext {
  trace_id: string
  total: number
  items: LogContextItem[]
}

/* ---------- metrics ---------- */

export interface MetricDefinition {
  id: EntityId
  metric_key: string
  metric_name: string
  metric_type: string
  unit: string | null
  description: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface MetricSeriesPoint {
  timestamp: IsoDateTime
  value: number
  min_value: number
  max_value: number
  sum_value: number
  sample_count: number
}

/* ---------- events ---------- */

export interface OpsEvent {
  id: EntityId
  event_id: string
  event_type: string
  source: string
  resource_type: string | null
  resource_id: EntityId | null
  severity: string
  message: string | null
  trace_id: string | null
  request_id: string | null
  occurred_at: IsoDateTime
  metadata: Record<string, unknown> | null
  created_at: IsoDateTime
}

/* ---------- alerts ---------- */

export interface Alert {
  id: EntityId
  fingerprint: string
  rule_id: EntityId | null
  alert_type: string
  severity: string
  status: string
  resource_type: string | null
  resource_id: EntityId | null
  host_id: EntityId | null
  service_id: EntityId | null
  metric_key: string | null
  metric_value: number | null
  threshold: number | null
  description: string | null
  trace_id: string | null
  triggered_at: IsoDateTime
  acknowledged_at: IsoDateTime | null
  acknowledged_by: EntityId | null
  silenced_until: IsoDateTime | null
  silence_reason: string | null
  resolved_at: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface AlertRule {
  id: EntityId
  rule_code: string
  rule_name: string
  alert_type: string
  metric_key: string
  condition: string
  threshold: number
  duration_seconds: number
  severity: string
  scope_type: string
  scope_id: EntityId | null
  notification_policy: Record<string, unknown> | null
  enabled: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface AlertRuleCreateRequest {
  rule_code: string
  rule_name: string
  alert_type: string
  metric_key: string
  condition?: string
  threshold: number
  duration_seconds?: number
  severity?: string
  scope_type?: string
  scope_id?: string | null
  notification_policy?: Record<string, unknown> | null
  enabled?: boolean
}

export interface AlertRuleUpdateRequest {
  rule_name?: string | null
  alert_type?: string | null
  metric_key?: string | null
  condition?: string | null
  threshold?: number | null
  duration_seconds?: number | null
  severity?: string | null
  scope_type?: string | null
  scope_id?: string | null
  notification_policy?: Record<string, unknown> | null
  enabled?: boolean | null
}

export interface AlertAckRequest {
  note?: string | null
}

export interface AlertSilenceRequest {
  silence_minutes: number
  silence_reason: string
}

export interface AlertResolveRequest {
  note?: string | null
}

export interface AlertEvaluation {
  evaluated_rules: number
  firing: number
  resolved: number
  failed_rules: number
}

/** One notification attempt recorded for one alert. */
export interface AlertNotification {
  id: EntityId
  alert_id: EntityId
  channel_id: EntityId | null
  channel_code: string
  receiver: string | null
  status: string
  retry_count: number
  sent_at: IsoDateTime | null
  error_message: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/* ---------- notifications ---------- */

export interface NotificationChannel {
  id: EntityId
  channel_code: string
  channel_name: string
  channel_type: string
  config: Record<string, unknown>
  enabled: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface NotificationChannelCreateRequest {
  channel_code: string
  channel_name: string
  channel_type?: string
  config: Record<string, unknown>
  enabled?: boolean
}

export interface NotificationChannelUpdateRequest {
  channel_name?: string | null
  channel_type?: string | null
  config?: Record<string, unknown> | null
  enabled?: boolean | null
}

/* ---------- maintenance ---------- */

export interface MaintenanceWindow {
  id: EntityId
  window_code: string
  title: string
  reason: string | null
  scope_type: string
  scope_id: EntityId | null
  starts_at: IsoDateTime
  ends_at: IsoDateTime
  suppress_alerts: boolean
  enabled: boolean
  created_by: EntityId | null
  created_by_username: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface MaintenanceWindowCreateRequest {
  window_code: string
  title: string
  reason?: string | null
  scope_type?: string
  scope_id?: string | null
  starts_at: IsoDateTime
  ends_at: IsoDateTime
  suppress_alerts?: boolean
  enabled?: boolean
}

export interface MaintenanceWindowUpdateRequest {
  title?: string | null
  reason?: string | null
  scope_type?: string | null
  scope_id?: string | null
  starts_at?: IsoDateTime | null
  ends_at?: IsoDateTime | null
  suppress_alerts?: boolean | null
  enabled?: boolean | null
}

/* ---------- agents ---------- */

export interface Agent {
  id: EntityId
  agent_code: string
  agent_name: string
  host_id: EntityId | null
  version: string | null
  ip_address: string | null
  status: string
  enabled: boolean
  last_heartbeat_at: IsoDateTime | null
  registered_at: IsoDateTime | null
  metadata: Record<string, unknown> | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/**
 * A registered agent plus the plain token, returned exactly once.
 *
 * The token is not persisted anywhere, so the registration response is the only
 * chance a caller has to store it.
 */
export interface AgentRegisterResult extends Agent {
  token: string
}

export interface AgentCreateRequest {
  agent_code: string
  agent_name: string
  host_id?: string | null
  version?: string | null
  metadata?: Record<string, unknown> | null
}

export interface AgentHeartbeat {
  id: EntityId
  agent_id: EntityId
  cpu_usage: number | null
  memory_usage: number | null
  disk_usage: number | null
  load1: number | null
  load5: number | null
  load15: number | null
  net_rx_bytes: number | null
  net_tx_bytes: number | null
  uptime_seconds: number | null
  collected_at: IsoDateTime
  created_at: IsoDateTime
}

/* ---------- availability ---------- */

export interface AvailabilityCheck {
  id: EntityId
  check_code: string
  name: string
  check_type: string
  target: string
  service_id: EntityId | null
  environment: string
  timeout_ms: number
  interval_seconds: number
  expected_status: number | null
  enabled: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface AvailabilityCheckCreateRequest {
  check_code: string
  name: string
  check_type: string
  target: string
  service_id?: string | null
  environment?: string
  timeout_ms?: number
  interval_seconds?: number
  expected_status?: number | null
  enabled?: boolean
}

export interface AvailabilityCheckUpdateRequest {
  name?: string | null
  target?: string | null
  service_id?: string | null
  environment?: string | null
  timeout_ms?: number | null
  interval_seconds?: number | null
  expected_status?: number | null
  enabled?: boolean | null
}

export interface AvailabilityResult {
  id: EntityId
  check_id: EntityId
  success: boolean
  latency_ms: number | null
  status_code: number | null
  error_message: string | null
  detail: Record<string, unknown> | null
  checked_at: IsoDateTime
}

/* ---------- jobs ---------- */

export interface JobRun {
  id: EntityId
  job_code: string
  job_name: string
  job_type: string
  status: string
  priority: number
  attempt_count: number
  max_attempts: number
  available_at: IsoDateTime
  started_at: IsoDateTime | null
  finished_at: IsoDateTime | null
  duration_seconds: number | null
  last_error: string | null
  trace_id: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface JobStatistics {
  days: number
  window_start: IsoDateTime
  window_end: IsoDateTime
  total: number
  status_counts: Record<string, number>
  success_count: number
  failed_count: number
  cancelled_count: number
  running_count: number
  pending_count: number
  success_rate: number
  failure_rate: number
  avg_duration_seconds: number | null
  max_duration_seconds: number | null
  timeout_count: number
  consecutive_failed_count: number
}

/* ---------- audit ---------- */

export interface OpsAuditRecord {
  id: EntityId
  operator_id: EntityId | null
  operator_username: string | null
  action: string
  resource_type: string
  resource_id: EntityId | null
  result: string
  error_message: string | null
  ip_address: string | null
  user_agent: string | null
  trace_id: string | null
  request_id: string | null
  before_data: Record<string, unknown> | null
  after_data: Record<string, unknown> | null
  created_at: IsoDateTime
}

/* ---------- reports ---------- */

/** The window a report covers (`ReportWindow`). */
export interface ReportWindow {
  days: number
  start_at: IsoDateTime
  end_at: IsoDateTime
}

/** Host fleet distribution (`HostReport`). */
export interface ReportHostSummary {
  total: number
  online: number
  by_status: Record<string, number>
  online_rate: number
}

/** Service fleet health (`ServiceReport`). */
export interface ReportServiceSummary {
  total: number
  abnormal: number
  availability_rate: number
}

/** Alert volume and handling quality (`AlertReport`). */
export interface ReportAlertSummary {
  fired: number
  resolved: number
  active: number
  by_severity: Record<string, number>
  resolve_rate: number
  /** `null` when nothing was resolved in the window. */
  mttr_seconds: number | null
}

/** Availability probes inside the window (`AvailabilityReport`). */
export interface ReportAvailabilitySummary {
  check_count: number
  failure_count: number
  success_rate: number
}

/** Collection fleet snapshot (`AgentReport`). */
export interface ReportAgentSummary {
  total: number
  online: number
}

/** Headline numbers of the window (`ReportSummaryResponse`). */
export interface ReportSummary {
  window: ReportWindow
  host: ReportHostSummary
  service: ReportServiceSummary
  alert: ReportAlertSummary
  availability: ReportAvailabilitySummary
  agent: ReportAgentSummary
  generated_at: IsoDateTime
}

/** One day of the alert trend (`AlertTrendPoint`). */
export interface AlertTrendPoint {
  date: string
  fired: number
  resolved: number
  by_severity: Record<string, number>
}

/** Daily alert volume (`AlertTrendResponse`). */
export interface AlertTrend {
  window: ReportWindow
  points: AlertTrendPoint[]
  generated_at: IsoDateTime
}

/** One row of the noisy-resource ranking (`AlertRankingRow`). */
export interface AlertRankingRow {
  rank: number
  resource_type: string
  resource_id: EntityId | null
  alert_type: string
  total: number
  active: number
  worst_severity: string | null
  last_triggered_at: IsoDateTime | null
}

/** The noisiest resources (`AlertRankingResponse`). */
export interface AlertRanking {
  window: ReportWindow
  rows: AlertRankingRow[]
  generated_at: IsoDateTime
}

/** One availability probe (`AvailabilityRow`). */
export interface ReportAvailabilityRow {
  check_id: EntityId
  check_code: string
  name: string
  target: string
  total: number
  failed: number
  success_rate: number
  avg_latency_ms: number
  max_latency_ms: number
}

/** Per-probe availability (`AvailabilityReportResponse`). */
export interface ReportAvailability {
  window: ReportWindow
  rows: ReportAvailabilityRow[]
  generated_at: IsoDateTime
}

/** One host status bucket (`HostStatusRow`). */
export interface HostStatusRowValue {
  status: string
  count: number
  share: number
}

/** Host fleet status distribution (`HostStatusResponse`). */
export interface HostStatusDistribution {
  window: ReportWindow
  total: number
  rows: HostStatusRowValue[]
  generated_at: IsoDateTime
}

/** A rendered CSV document travelling inside the envelope. */
export interface ReportExport {
  report: string
  filename: string
  content_type: string
  content: string
  generated_at: IsoDateTime
}

/** Reports the CSV export can render. */
export type ExportableReport =
  | 'summary'
  | 'alert-trend'
  | 'alert-ranking'
  | 'availability'
  | 'host-status'
