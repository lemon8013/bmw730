import type { ToolDefinition } from '@/types/tool'

/** Raised when a tool definition cannot be registered. */
export class ToolRegistryError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ToolRegistryError'
  }
}

/**
 * Tool registry.
 *
 * Only safety vetted components are registered, and registration happens in code
 * at build time — never from remote input.
 */
export class ToolRegistry {
  private readonly definitions = new Map<string, ToolDefinition>()

  /** Register a single definition. Duplicate keys and empty component keys are rejected. */
  register(definition: ToolDefinition): void {
    if (definition.key.trim() === '') {
      throw new ToolRegistryError('tool key is required')
    }
    if (definition.componentKey.trim() === '') {
      throw new ToolRegistryError(`tool "${definition.key}" is missing a componentKey`)
    }
    if (this.definitions.has(definition.key)) {
      throw new ToolRegistryError(`tool "${definition.key}" is already registered`)
    }
    this.definitions.set(definition.key, Object.freeze({ ...definition }))
  }

  /** Register several definitions; the whole batch fails on the first conflict. */
  registerMany(definitions: readonly ToolDefinition[]): void {
    for (const definition of definitions) {
      this.register(definition)
    }
  }

  /** Remove a definition. Returns whether something was removed. */
  unregister(key: string): boolean {
    return this.definitions.delete(key)
  }

  /** Whether the key is registered. */
  has(key: string): boolean {
    return this.definitions.has(key)
  }

  /** Return a definition, or undefined when unknown. */
  get(key: string): ToolDefinition | undefined {
    return this.definitions.get(key)
  }

  /** All definitions in registration order. */
  list(): readonly ToolDefinition[] {
    return [...this.definitions.values()]
  }

  /** All registered keys in registration order. */
  keys(): readonly string[] {
    return [...this.definitions.keys()]
  }

  /** Number of registered definitions. */
  get size(): number {
    return this.definitions.size
  }
}

/** Application level registry instance. */
export const toolRegistry = new ToolRegistry()
