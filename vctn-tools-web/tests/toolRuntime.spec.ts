import type { ToolDefinition } from '@/types/tool'
import { ToolRegistry } from '@/tools/registry'
import {
  ToolExecutionModeError,
  ToolNotFoundError,
  ToolRuntime,
  ToolRuntimeError,
  type ToolRuntimeContext,
} from '@/tools/runtime'
import { describe, expect, it } from 'vitest'

const frontendTool: ToolDefinition = {
  key: 'sample.alpha',
  mode: 'FRONTEND',
  componentKey: 'SampleAlpha',
}

const asyncTool: ToolDefinition = {
  key: 'sample.beta',
  mode: 'ASYNC',
  componentKey: 'SampleBeta',
}

const context: ToolRuntimeContext = { traceId: 'trace-1', requestId: 'request-1' }

function buildRuntime(): ToolRuntime {
  const registry = new ToolRegistry()
  registry.registerMany([frontendTool, asyncTool])
  return new ToolRuntime(registry)
}

describe('ToolRuntime', () => {
  it('starts without any executor', () => {
    const runtime = buildRuntime()
    expect(runtime.modes()).toEqual([])
    expect(runtime.hasExecutor('FRONTEND')).toBe(false)
  })

  it('resolves a registered tool', () => {
    const runtime = buildRuntime()
    expect(runtime.resolve('sample.alpha').componentKey).toBe('SampleAlpha')
  })

  it('throws for an unknown tool', () => {
    const runtime = buildRuntime()
    expect(() => runtime.resolve('sample.unknown')).toThrow(ToolNotFoundError)
  })

  it('throws when the mode has no executor', async () => {
    const runtime = buildRuntime()
    await expect(runtime.execute('sample.alpha', null, context)).rejects.toThrow(
      ToolExecutionModeError,
    )
  })

  it('executes through the registered executor', async () => {
    const runtime = buildRuntime()
    runtime.registerExecutor('FRONTEND', (input, runtimeContext) => ({
      echoed: input,
      traceId: runtimeContext.traceId,
    }))

    expect(runtime.hasExecutor('FRONTEND')).toBe(true)
    expect(runtime.modes()).toEqual(['FRONTEND'])

    const result = await runtime.execute('sample.alpha', { value: 1 }, context)
    expect(result.toolKey).toBe('sample.alpha')
    expect(result.mode).toBe('FRONTEND')
    expect(result.output).toEqual({ echoed: { value: 1 }, traceId: 'trace-1' })
  })

  it('routes each mode to its own executor', async () => {
    const runtime = buildRuntime()
    runtime.registerExecutor('FRONTEND', () => 'frontend')
    runtime.registerExecutor('ASYNC', async () => 'async')

    await expect(runtime.execute('sample.alpha', null, context)).resolves.toMatchObject({
      output: 'frontend',
    })
    await expect(runtime.execute('sample.beta', null, context)).resolves.toMatchObject({
      output: 'async',
    })
  })

  it('rejects a second executor for the same mode', () => {
    const runtime = buildRuntime()
    runtime.registerExecutor('FRONTEND', () => null)
    expect(() => runtime.registerExecutor('FRONTEND', () => null)).toThrow(ToolRuntimeError)
  })

  it('propagates an executor failure', async () => {
    const runtime = buildRuntime()
    runtime.registerExecutor('FRONTEND', () => {
      throw new Error('tool failed')
    })
    await expect(runtime.execute('sample.alpha', null, context)).rejects.toThrow('tool failed')
  })
})
