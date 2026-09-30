import type { ToolDefinition, ToolExecutionMode } from '@/types/tool'
import { ToolRegistry } from '@/tools/registry/ToolRegistry'

/** Raised when the runtime cannot fulfil an execution request. */
export class ToolRuntimeError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ToolRuntimeError'
  }
}

/** Raised when the requested tool is not registered. */
export class ToolNotFoundError extends ToolRuntimeError {
  constructor(message: string) {
    super(message)
    this.name = 'ToolNotFoundError'
  }
}

/** Raised when no executor is registered for the tool execution mode. */
export class ToolExecutionModeError extends ToolRuntimeError {
  constructor(message: string) {
    super(message)
    this.name = 'ToolExecutionModeError'
  }
}

/** Per execution identifiers, taken from the request trace context. */
export interface ToolRuntimeContext {
  readonly traceId: string
  readonly requestId: string
}

/** Executes one tool. Phase 0 registers no executor. */
export type ToolExecutor = (
  input: unknown,
  context: ToolRuntimeContext,
) => Promise<unknown> | unknown

/** Result of one execution. */
export interface ToolExecutionResult {
  readonly toolKey: string
  readonly mode: ToolExecutionMode
  readonly output: unknown
}

/**
 * Tool runtime.
 *
 * Resolves a tool definition from the registry and dispatches it to the executor
 * registered for the tool execution mode. Concrete tools are implemented in a
 * later phase; this class only provides the frozen execution contract.
 */
export class ToolRuntime {
  private readonly registry: ToolRegistry
  private readonly executors = new Map<ToolExecutionMode, ToolExecutor>()

  constructor(registry: ToolRegistry) {
    this.registry = registry
  }

  /** Register the executor for one mode. One executor per mode. */
  registerExecutor(mode: ToolExecutionMode, executor: ToolExecutor): void {
    if (this.executors.has(mode)) {
      throw new ToolRuntimeError(`an executor is already registered for mode "${mode}"`)
    }
    this.executors.set(mode, executor)
  }

  /** Whether an executor exists for the mode. */
  hasExecutor(mode: ToolExecutionMode): boolean {
    return this.executors.has(mode)
  }

  /** Modes that currently have an executor. */
  modes(): readonly ToolExecutionMode[] {
    return [...this.executors.keys()]
  }

  /** Resolve a definition, or throw when the tool is unknown. */
  resolve(key: string): ToolDefinition {
    const definition = this.registry.get(key)
    if (definition === undefined) {
      throw new ToolNotFoundError(`tool "${key}" is not registered`)
    }
    return definition
  }

  /** Execute a registered tool through its mode executor. */
  async execute(
    key: string,
    input: unknown,
    context: ToolRuntimeContext,
  ): Promise<ToolExecutionResult> {
    const definition = this.resolve(key)
    const executor = this.executors.get(definition.mode)
    if (executor === undefined) {
      throw new ToolExecutionModeError(`no executor registered for mode "${definition.mode}"`)
    }
    const output = await executor(input, context)
    return { toolKey: definition.key, mode: definition.mode, output }
  }
}
