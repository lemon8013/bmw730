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
  /**
   * Not frozen: the workbench form for this component. Registration still
   * happens in code at build time — never from remote input.
   */
  readonly fields?: readonly ToolFieldDescriptor[]
  /** Not frozen: how the workbench renders the execution output. */
  readonly output?: ToolOutputKind
}

/** Kind of one workbench input field. */
export type ToolFieldKind = 'textarea' | 'text' | 'number' | 'select' | 'switch'

/** One workbench input field descriptor. */
export interface ToolFieldDescriptor {
  /** Key inside the `inputs` payload sent to the runtime. */
  readonly name: string
  readonly label: string
  readonly kind: ToolFieldKind
  readonly required?: boolean
  readonly placeholder?: string
  readonly help?: string
  readonly defaultValue?: string | number | boolean
  readonly options?: readonly { readonly label: string; readonly value: string }[]
  readonly min?: number
  readonly max?: number
  /** Only show this field when another field has one of these values. */
  readonly showWhen?: { readonly field: string; readonly equals: readonly string[] }
}

/** How the workbench renders one execution output. */
export type ToolOutputKind =
  | 'text'
  | 'values'
  | 'digest'
  | 'stats'
  | 'regex'
  | 'jwt'
  | 'datetime'
  | 'codepoints'
  | 'markdown'
  | 'json'
  | 'echo'
  | 'job'
