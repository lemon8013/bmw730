/**
 * Column visibility and ordering for every list table.
 *
 * The console has one table component, so the preference is stored once and
 * keyed by the table rather than by the page. A table's columns are discovered
 * from the `ElTableColumn` children it was given, which keeps pages free of any
 * bookkeeping: whatever columns a page declares are exactly the ones the user
 * can show, hide and reorder.
 */

import { Comment, Fragment, type VNode } from 'vue'

/** One configurable column of a table. */
export interface TableColumnMeta {
  /** Stable identity of the column, derived from its `prop` (or label). */
  key: string
  /** Header text shown in the settings panel. */
  label: string
  /**
   * Structural columns (`selection`, `index`, `expand`) are always rendered and
   * are never offered for configuration.
   */
  structural: boolean
}

/** Persisted preference of one table. */
export interface TableSettings {
  /** Column keys in display order. */
  order: string[]
  /** Keys the user hid; everything absent is visible. */
  hidden: string[]
}

const STORAGE_PREFIX = 'vctn.admin.table.'

/** Column types that are part of the table mechanics, not the data. */
const STRUCTURAL_TYPES: readonly string[] = ['selection', 'index', 'expand']

const EMPTY_SETTINGS: TableSettings = { order: [], hidden: [] }

function readString(value: unknown): string | null {
  if (typeof value === 'string' && value.trim().length > 0) {
    return value.trim()
  }
  if (typeof value === 'number') {
    return String(value)
  }
  return null
}

/** Flatten fragment/`v-for` wrappers down to the real column vnodes. */
export function flattenColumnNodes(nodes: readonly VNode[]): VNode[] {
  const collected: VNode[] = []
  for (const node of nodes) {
    if (node.type === Comment) {
      // A `v-if="false"` column.
      continue
    }
    if (node.type === Fragment) {
      const children = node.children
      if (Array.isArray(children)) {
        collected.push(...flattenColumnNodes(children as VNode[]))
      }
      continue
    }
    collected.push(node)
  }
  return collected
}

/** Describe one column vnode. */
export function describeColumn(node: VNode): TableColumnMeta {
  const props = (node.props ?? {}) as Record<string, unknown>
  const prop = readString(props.prop) ?? readString(props.columnKey)
  const label = readString(props.label) ?? prop ?? '列'
  const type = readString(props.type)
  const structural = type !== null && STRUCTURAL_TYPES.includes(type)
  // `prop` is the stable identity; a column without one falls back to its
  // header, which is unique in practice for a hand-declared table.
  return { key: prop ?? `label:${label}`, label, structural }
}

/** Describe every configurable column of a table, in declaration order. */
export function describeColumns(nodes: readonly VNode[]): TableColumnMeta[] {
  const seen = new Set<string>()
  const metas: TableColumnMeta[] = []
  for (const node of flattenColumnNodes(nodes)) {
    const meta = describeColumn(node)
    if (meta.structural || seen.has(meta.key)) {
      continue
    }
    seen.add(meta.key)
    metas.push(meta)
  }
  return metas
}

/** Attach a stable key to each column vnode, keeping declaration order. */
export function keyColumnNodes(nodes: readonly VNode[]): { meta: TableColumnMeta; node: VNode }[] {
  const seen = new Set<string>()
  const entries: { meta: TableColumnMeta; node: VNode }[] = []
  for (const node of flattenColumnNodes(nodes)) {
    const meta = describeColumn(node)
    if (meta.structural || seen.has(meta.key)) {
      continue
    }
    seen.add(meta.key)
    entries.push({ meta, node })
  }
  return entries
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

/** Read the stored preference of one table, tolerating a corrupted entry. */
export function loadTableSettings(tableKey: string): TableSettings {
  try {
    const raw = window.localStorage.getItem(`${STORAGE_PREFIX}${tableKey}`)
    if (raw === null) {
      return { ...EMPTY_SETTINGS }
    }
    const parsed: unknown = JSON.parse(raw)
    if (parsed === null || typeof parsed !== 'object') {
      return { ...EMPTY_SETTINGS }
    }
    const record = parsed as { order?: unknown; hidden?: unknown }
    return {
      order: isStringArray(record.order) ? [...record.order] : [],
      hidden: isStringArray(record.hidden) ? [...record.hidden] : [],
    }
  } catch {
    return { ...EMPTY_SETTINGS }
  }
}

/** Persist the preference of one table. */
export function saveTableSettings(tableKey: string, settings: TableSettings): void {
  try {
    window.localStorage.setItem(`${STORAGE_PREFIX}${tableKey}`, JSON.stringify(settings))
  } catch {
    // A full or unavailable storage must not break the table.
  }
}

/** The table key for a route path, used when a page declares nothing. */
export function tableKeyFromPath(path: string): string {
  return path.replace(/^\//, '').replace(/\//g, '.') || 'root'
}

/**
 * Bring a stored preference in line with the columns a table actually has.
 *
 * Columns that no longer exist are dropped; new columns are appended where the
 * page declared them. Unknown keys never hide a column.
 */
export function reconcileSettings(
  metas: readonly TableColumnMeta[],
  stored: TableSettings,
): TableSettings {
  const known = new Set(metas.map((meta) => meta.key))
  const order = stored.order.filter((key) => known.has(key))
  for (const meta of metas) {
    if (!order.includes(meta.key)) {
      order.push(meta.key)
    }
  }
  const hidden = stored.hidden.filter((key) => known.has(key))
  return { order, hidden }
}

/** Order the column vnodes and drop the hidden ones. */
export function applySettings(
  entries: readonly { meta: TableColumnMeta; node: VNode }[],
  settings: TableSettings,
): VNode[] {
  const hidden = new Set(settings.hidden)
  const position = new Map(settings.order.map((key, index) => [key, index]))
  return [...entries]
    .filter((entry) => !hidden.has(entry.meta.key))
    .sort((left, right) => {
      const a = position.get(left.meta.key) ?? Number.MAX_SAFE_INTEGER
      const b = position.get(right.meta.key) ?? Number.MAX_SAFE_INTEGER
      return a - b
    })
    .map((entry) => entry.node)
}
