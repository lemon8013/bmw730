<script setup lang="ts">
/**
 * Read-only JSON display for audit `before_data` / `after_data`.
 *
 * Values whose key looks like a credential are replaced before rendering, so a
 * payload that should never have contained a secret still cannot leak one into
 * the DOM.
 */
import { computed } from 'vue'

const SENSITIVE_KEY_PATTERN =
  /(password|passwd|secret|token|credential|authorization|cookie|api[_-]?key|private[_-]?key)/i

interface Props {
  value: unknown
  /** Number of spaces used when the payload had to be re-serialised. */
  indent?: number
}

const props = withDefaults(defineProps<Props>(), { indent: 2 })

function mask(value: unknown, depth: number): unknown {
  if (depth > 12) {
    return '[too deep]'
  }
  if (Array.isArray(value)) {
    return value.map((item) => mask(item, depth + 1))
  }
  if (value !== null && typeof value === 'object') {
    const result: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      result[key] = SENSITIVE_KEY_PATTERN.test(key) ? '[REDACTED]' : mask(item, depth + 1)
    }
    return result
  }
  return value
}

const rendered = computed<string>(() => {
  if (props.value === null || props.value === undefined) {
    return '—'
  }
  try {
    return JSON.stringify(mask(props.value, 0), null, props.indent)
  } catch {
    return '[无法序列化]'
  }
})
</script>

<template>
  <pre class="json-viewer">{{ rendered }}</pre>
</template>

<style scoped>
.json-viewer {
  max-height: 360px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--vctn-border-subtle);
  border-radius: 4px;
  background-color: var(--vctn-bg-hover);
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
