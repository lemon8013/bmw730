import { describe, expect, it } from 'vitest'

import { toolDefinitions } from '@/tools/definitions'
import { ToolRegistry } from '@/tools/registry'
import type { ToolDefinition, ToolFieldDescriptor, ToolOutputKind } from '@/types/tool'

const FIELD_KINDS = new Set(['textarea', 'text', 'number', 'select', 'switch'])

const OUTPUT_KINDS = new Set<ToolOutputKind>([
  'text',
  'values',
  'digest',
  'stats',
  'regex',
  'jwt',
  'datetime',
  'codepoints',
  'markdown',
  'json',
  'echo',
  'job',
])

/** component_key values shipped by `vctn-api/app/tools/runtime/providers.py`. */
const BACKEND_COMPONENT_KEYS = new Set([
  'json.format',
  'xml.format',
  'toml.parse',
  'base64.codec',
  'url.codec',
  'uuid.generate',
  'ulid.generate',
  'hash.digest',
  'regex.test',
  'jwt.parse',
  'text.stats',
  'datetime.convert',
  'random.string',
  'password.generate',
  'unicode.inspect',
  'markdown.render',
  'frontend.echo',
  'async.job',
])

function fieldNames(definition: ToolDefinition): string[] {
  return (definition.fields ?? []).map((field: ToolFieldDescriptor) => field.name)
}

describe('built-in tool definitions', () => {
  it('covers every backend component key', () => {
    expect(new Set(toolDefinitions.map((definition) => definition.key))).toEqual(
      BACKEND_COMPONENT_KEYS,
    )
  })

  it('keeps key and componentKey aligned', () => {
    for (const definition of toolDefinitions) {
      expect(definition.componentKey, definition.key).toBe(definition.key)
    }
  })

  it('gives every definition a workbench form and output kind', () => {
    for (const definition of toolDefinitions) {
      expect(definition.fields?.length ?? 0, definition.key).toBeGreaterThan(0)
      expect(OUTPUT_KINDS.has(definition.output as ToolOutputKind), definition.key).toBe(true)
      for (const field of definition.fields ?? []) {
        expect(FIELD_KINDS.has(field.kind), `${definition.key}.${field.name}`).toBe(true)
        if (field.kind === 'select') {
          expect(field.options?.length ?? 0, `${definition.key}.${field.name}`).toBeGreaterThan(0)
        }
        if (field.showWhen !== undefined) {
          expect(
            fieldNames(definition),
            `${definition.key}.${field.name}`,
          ).toContain(field.showWhen.field)
        }
      }
    }
  })

  it('registers cleanly into a registry', () => {
    // A fresh instance: registration happens in main.ts at bootstrap, not on import.
    const registry = new ToolRegistry()
    registry.registerMany(toolDefinitions)
    expect(registry.size).toBe(toolDefinitions.length)
    for (const definition of toolDefinitions) {
      expect(registry.get(definition.key)).toBeDefined()
    }
  })

  it('rejects a duplicate registration', () => {
    const registry = new ToolRegistry()
    registry.registerMany(toolDefinitions)
    expect(() => registry.register(toolDefinitions[0]!)).toThrow(/already registered/)
  })
})
