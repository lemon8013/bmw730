import type { ToolDefinition } from '@/types/tool'
import { ToolRegistry, ToolRegistryError } from '@/tools/registry'
import { describe, expect, it } from 'vitest'

const alpha: ToolDefinition = {
  key: 'sample.alpha',
  mode: 'FRONTEND',
  componentKey: 'SampleAlpha',
}

const beta: ToolDefinition = {
  key: 'sample.beta',
  mode: 'BACKEND',
  componentKey: 'SampleBeta',
}

describe('ToolRegistry', () => {
  it('starts empty', () => {
    const registry = new ToolRegistry()
    expect(registry.size).toBe(0)
    expect(registry.list()).toEqual([])
    expect(registry.keys()).toEqual([])
  })

  it('registers and resolves a definition', () => {
    const registry = new ToolRegistry()
    registry.register(alpha)

    expect(registry.size).toBe(1)
    expect(registry.has('sample.alpha')).toBe(true)
    expect(registry.get('sample.alpha')?.componentKey).toBe('SampleAlpha')
    expect(registry.get('sample.unknown')).toBeUndefined()
  })

  it('freezes a registered definition', () => {
    const registry = new ToolRegistry()
    registry.register(alpha)
    expect(Object.isFrozen(registry.get('sample.alpha'))).toBe(true)
  })

  it('rejects a duplicate key', () => {
    const registry = new ToolRegistry()
    registry.register(alpha)
    expect(() => registry.register(alpha)).toThrow(ToolRegistryError)
  })

  it('rejects an empty key', () => {
    const registry = new ToolRegistry()
    expect(() =>
      registry.register({ key: '  ', mode: 'FRONTEND', componentKey: 'X' }),
    ).toThrow(ToolRegistryError)
  })

  it('rejects a definition without a component key', () => {
    const registry = new ToolRegistry()
    expect(() =>
      registry.register({ key: 'sample.gamma', mode: 'ASYNC', componentKey: '' }),
    ).toThrow(ToolRegistryError)
  })

  it('registers a batch in order', () => {
    const registry = new ToolRegistry()
    registry.registerMany([alpha, beta])
    expect(registry.keys()).toEqual(['sample.alpha', 'sample.beta'])
    expect(registry.list().map((item) => item.mode)).toEqual(['FRONTEND', 'BACKEND'])
  })

  it('fails the whole batch on a conflict', () => {
    const registry = new ToolRegistry()
    expect(() => registry.registerMany([alpha, alpha])).toThrow(ToolRegistryError)
  })

  it('unregisters a definition', () => {
    const registry = new ToolRegistry()
    registry.register(alpha)
    expect(registry.unregister('sample.alpha')).toBe(true)
    expect(registry.unregister('sample.alpha')).toBe(false)
    expect(registry.size).toBe(0)
  })
})
