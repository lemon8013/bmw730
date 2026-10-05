/**
 * Tool execution wire format (`app/tools/runtime`).
 */

import type { EntityId } from '@/types/api'

/** `POST /tools/runtime/execute/{tool_id}` request body. */
export interface ToolExecuteRequest {
  readonly inputs: Record<string, unknown>
  /** Identifies an anonymous caller; the console persists one in localStorage. */
  readonly anonymous_id?: string
  readonly idempotency_key?: string
}

/** `POST /tools/runtime/execute/{tool_id}` response payload. */
export interface ToolExecuteResponse {
  readonly tool_id: EntityId
  readonly usage_event_id: EntityId | null
  /** Set for ASYNC tools: the queued job that will run the tool later. */
  readonly job_id: EntityId | null
  readonly success: boolean
  readonly output: unknown
  readonly duration_ms: number
  readonly error_code: string | null
  readonly error_message: string | null
  readonly execution_mode: string
}

/** One asynchronous tool job (`GET /tools/jobs/{job_id}`). */
export interface ToolJobItem {
  readonly id: EntityId
  readonly job_code: string
  readonly job_name: string
  readonly job_type: string
  readonly status: string
  readonly priority: number
  readonly attempt_count: number
  readonly max_attempts: number
  readonly available_at: string
  readonly started_at: string | null
  readonly finished_at: string | null
  readonly last_error: string | null
  readonly trace_id: string | null
  readonly created_at: string
  readonly updated_at: string
  readonly payload: Record<string, unknown> | null
}
