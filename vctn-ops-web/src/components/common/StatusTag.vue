<script setup lang="ts">
/**
 * Render any backend status / result / severity value as a coloured tag.
 *
 * Every status-like column in the console goes through this component, so a
 * value is never shown as bare text and the same value always gets the same
 * colour. Domain specific wording can be supplied through `labels` when the
 * generic `STATUS_LABEL` entry would be wrong for the field.
 */
import { computed } from 'vue'
import { ElTag } from 'element-plus'

import { STATUS_LABEL, STATUS_TAG_TYPE, type TagTone } from '@/types/enums'

interface Props {
  value: string | number | boolean | null | undefined
  /** Overrides the generic label for this value. */
  labels?: Readonly<Record<string, string>>
  /** Label used when the value is empty. */
  fallback?: string
  /** Render `false`/`true` for boolean columns with these labels. */
  booleanLabels?: readonly [string, string]
}

const props = withDefaults(defineProps<Props>(), {
  labels: undefined,
  fallback: '—',
  booleanLabels: undefined,
})

/** A boolean column is a two-state value set, not a missing one. */
function toneOf(raw: string): TagTone {
  if (raw === 'true') {
    return 'success'
  }
  if (raw === 'false') {
    return 'info'
  }
  return STATUS_TAG_TYPE[raw] ?? 'info'
}

function labelOf(raw: string): string {
  if (props.booleanLabels !== undefined && (raw === 'true' || raw === 'false')) {
    const [off, on] = props.booleanLabels
    return raw === 'true' ? on : off
  }
  if (props.labels !== undefined && props.labels[raw] !== undefined) {
    return props.labels[raw]
  }
  if (STATUS_LABEL[raw] !== undefined) {
    return STATUS_LABEL[raw]
  }
  // An unmapped value is shown verbatim rather than hidden: an unknown status
  // is information the operator needs, not something to blank out.
  return raw
}

const raw = computed(() =>
  props.value === null || props.value === undefined ? '' : String(props.value),
)

const label = computed(() => (raw.value === '' ? props.fallback : labelOf(raw.value)))

const type = computed<TagTone>(() => (raw.value === '' ? 'info' : toneOf(raw.value)))
</script>

<template>
  <ElTag :type="type" size="small" effect="light" disable-transitions>{{ label }}</ElTag>
</template>
