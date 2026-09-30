/**
 * Tool concepts that the Spec freezes.
 *
 * Frozen: ToolRegistry, ToolRuntime, component_key and the
 * FRONTEND / BACKEND / ASYNC execution modes.
 *
 * Not frozen: the final Tool API DTO. The remaining ToolDefinition fields are
 * therefore intentionally not declared here.
 */

/** Where a tool executes. */
export type ToolExecutionMode = 'FRONTEND' | 'BACKEND' | 'ASYNC'

/** Every execution mode, in declaration order. */
export const TOOL_EXECUTION_MODES: readonly ToolExecutionMode[] = [
  'FRONTEND',
  'BACKEND',
  'ASYNC',
]

/** A tool the registry knows about. */
export interface ToolDefinition {
  /** Frozen: unique tool identifier. */
  readonly key: string
  /** Frozen: where the tool executes. */
  readonly mode: ToolExecutionMode
  /** Frozen: whitelisted frontend component key. */
  readonly componentKey: string
}
