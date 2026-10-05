/**
 * Built-in executors for the three frozen execution modes.
 *
 * BACKEND / ASYNC post to the single runtime endpoint; FRONTEND computes in the
 * browser first and only sends the produced result, so raw input never leaves
 * the device for frontend tools.
 */

import { executeTool } from '@/api/tools'
import type { ToolExecuteResponse } from '@/types/execution'
import type { ToolExecutor } from '@/tools/runtime/ToolRuntime'

/** Everything an executor needs to run one tool. */
export interface WorkbenchInput {
  readonly toolId: string
  readonly values: Record<string, unknown>
  readonly anonymousId: string
  /** FRONTEND tools only: produce the result locally before posting it. */
  computeLocal?: (values: Record<string, unknown>) => unknown
}

async function executeBackend(input: WorkbenchInput): Promise<ToolExecuteResponse> {
  return executeTool(input.toolId, { inputs: input.values, anonymous_id: input.anonymousId })
}

async function executeFrontend(input: WorkbenchInput): Promise<ToolExecuteResponse> {
  if (input.computeLocal === undefined) {
    throw new Error('a frontend tool needs a local compute function')
  }
  const result = input.computeLocal(input.values)
  // The backend validates the shape and records usage; it never recomputes.
  return executeTool(input.toolId, {
    inputs: { result },
    anonymous_id: input.anonymousId,
  })
}

async function executeAsync(input: WorkbenchInput): Promise<ToolExecuteResponse> {
  // The backend refuses inline execution and queues a job instead; the response
  // carries the job id the workbench can poll.
  return executeTool(input.toolId, { inputs: input.values, anonymous_id: input.anonymousId })
}

/** Register the executor for every mode. Call once during bootstrap. */
export function registerBuiltinExecutors(register: (mode: 'FRONTEND' | 'BACKEND' | 'ASYNC', executor: ToolExecutor) => void): void {
  register('BACKEND', (raw) => executeBackend(raw as WorkbenchInput))
  register('FRONTEND', (raw) => executeFrontend(raw as WorkbenchInput))
  register('ASYNC', (raw) => executeAsync(raw as WorkbenchInput))
}
