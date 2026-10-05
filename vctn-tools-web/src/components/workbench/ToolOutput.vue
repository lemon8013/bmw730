<script setup lang="ts">
/** Renders one execution output according to the registered output kind. */
import { computed } from 'vue'
import { ElAlert, ElDescriptions, ElDescriptionsItem, ElTable, ElTableColumn, ElTag } from 'element-plus'

import type { ToolOutputKind } from '@/types/tool'

const props = defineProps<{
  kind: ToolOutputKind
  output: unknown
}>()

function asRecord(value: unknown): Record<string, unknown> {
  return (value !== null && typeof value === 'object' ? value : {}) as Record<string, unknown>
}

function asText(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  return JSON.stringify(value, null, 2)
}

const record = computed(() => asRecord(props.output))

/** Text produced for copy / download buttons. */
const plainText = computed(() => {
  switch (props.kind) {
    case 'text':
    case 'echo':
      return asText(record.value.text ?? props.output)
    case 'values':
      return (Array.isArray(record.value.values) ? record.value.values : []).join('\n')
    case 'digest':
      return String(record.value.digest ?? '')
    case 'json':
      return JSON.stringify(record.value.value ?? props.output, null, 2)
    case 'markdown':
      return String(record.value.markdown ?? '')
    case 'regex':
    case 'stats':
    case 'datetime':
    case 'jwt':
    case 'codepoints':
      return JSON.stringify(props.output, null, 2)
    default:
      return asText(props.output)
  }
})

defineExpose({ plainText })

const valuesMeta = computed(() => {
  const value = record.value
  const rows: { label: string; value: string }[] = []
  if (value.entropy_bits !== undefined) {
    rows.push({ label: '熵：', value: `${value.entropy_bits} bits` })
  }
  if (value.alphabet_size !== undefined) {
    rows.push({ label: '字符集：', value: `${value.alphabet_size} 个字符` })
  }
  if (value.length !== undefined) {
    rows.push({ label: '长度：', value: `${value.length}` })
  }
  return rows
})

const statsRows = computed(() => {
  const value = record.value
  return [
    { label: '字符数', value: String(value.characters ?? '—') },
    { label: '不含空格', value: String(value.characters_no_spaces ?? '—') },
    { label: '词数', value: String(value.words ?? '—') },
    { label: '行数', value: String(value.lines ?? '—') },
    { label: '字节数 (UTF-8)', value: String(value.bytes ?? '—') },
  ]
})

const datetimeRows = computed(() => {
  const value = record.value
  return [
    { label: 'ISO 8601', value: String(value.iso ?? '—') },
    { label: '秒级时间戳', value: String(value.epoch_seconds ?? '—') },
    { label: '毫秒级时间戳', value: String(value.epoch_milliseconds ?? '—') },
  ]
})

const codePointRows = computed(() =>
  (Array.isArray(record.value.code_points) ? record.value.code_points : []).map(
    (point: number, index: number) => ({
      index: index + 1,
      character: String.fromCodePoint(point),
      codePoint: `U+${point.toString(16).toUpperCase().padStart(4, '0')}`,
      decimal: point,
    }),
  ),
)

const jwtHeader = computed(() => JSON.stringify(record.value.header ?? {}, null, 2))
const jwtPayload = computed(() => JSON.stringify(record.value.payload ?? {}, null, 2))
</script>

<template>
  <div class="tool-output">
    <!-- Plain / code-like outputs -->
    <pre v-if="kind === 'text' || kind === 'echo'" class="tool-output__code">{{ record.text ?? output }}</pre>

    <div v-else-if="kind === 'values'" class="tool-output__values-block">
      <div v-if="valuesMeta.length > 0" class="tool-output__meta">
        <span v-for="meta in valuesMeta" :key="meta.label" class="tool-output__meta-item">
          {{ meta.label }} <strong>{{ meta.value }}</strong>
        </span>
      </div>
      <div class="tool-output__values">
        <code v-for="item in record.values ?? []" :key="String(item)" class="tool-output__chip">
          {{ item }}
        </code>
      </div>
    </div>

    <div v-else-if="kind === 'digest'" class="tool-output__code tool-output__digest">
      <ElTag size="small" type="info">{{ record.algorithm }}</ElTag>
      <code>{{ record.digest }}</code>
    </div>

    <pre v-else-if="kind === 'json'" class="tool-output__code">{{ plainText }}</pre>

    <ElDescriptions v-else-if="kind === 'stats'" :column="1" border>
      <ElDescriptionsItem v-for="row in statsRows" :key="row.label" :label="row.label">
        {{ row.value }}
      </ElDescriptionsItem>
    </ElDescriptions>

    <ElDescriptions v-else-if="kind === 'datetime'" :column="1" border>
      <ElDescriptionsItem v-for="row in datetimeRows" :key="row.label" :label="row.label">
        {{ row.value }}
      </ElDescriptionsItem>
    </ElDescriptions>

    <template v-else-if="kind === 'regex'">
      <div class="tool-output__regex-summary">
        <ElTag :type="record.is_match ? 'success' : 'info'" size="small">
          {{ record.is_match ? '匹配' : '无匹配' }}
        </ElTag>
        <span>共 {{ record.match_count ?? 0 }} 处</span>
      </div>
      <div class="tool-output__values">
        <code v-for="(item, index) in record.matches ?? []" :key="`${item}-${index}`" class="tool-output__chip">
          {{ item }}
        </code>
      </div>
    </template>

    <template v-else-if="kind === 'jwt'">
      <h4 class="tool-output__subtitle">Header</h4>
      <pre class="tool-output__code">{{ jwtHeader }}</pre>
      <h4 class="tool-output__subtitle">Payload</h4>
      <pre class="tool-output__code">{{ jwtPayload }}</pre>
    </template>

    <ElTable v-else-if="kind === 'codepoints'" :data="codePointRows" size="small" max-height="360">
      <ElTableColumn prop="index" label="#" width="70" />
      <ElTableColumn prop="character" label="字符" width="90" />
      <ElTableColumn prop="codePoint" label="码点" width="130" />
      <ElTableColumn prop="decimal" label="十进制" />
    </ElTable>

    <!-- Server rendered (and sanitized) HTML from markdown.render -->
    <!-- eslint-disable-next-line vue/no-v-html -- the backend bleaches the HTML against a fixed whitelist -->
    <div v-else-if="kind === 'markdown'" class="tool-output__markdown" v-html="record.html" />

    <ElAlert v-else type="info" :closable="false" :title="'输出已返回（未识别的展示类型）'">
      <pre class="tool-output__code">{{ plainText }}</pre>
    </ElAlert>
  </div>
</template>

<style scoped>
.tool-output__code {
  margin: 0;
  padding: 12px 14px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 420px;
  overflow: auto;
}

.tool-output__values-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-output__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.tool-output__meta-item strong {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.tool-output__values {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tool-output__chip {
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  word-break: break-all;
}

.tool-output__digest {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool-output__regex-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tool-output__subtitle {
  margin: 12px 0 8px;
  font-size: 14px;
}

.tool-output__markdown {
  padding: 12px 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: #fff;
  overflow: auto;
}

.tool-output__markdown :deep(pre) {
  background: var(--el-fill-color-light);
  padding: 10px;
  border-radius: 6px;
  overflow: auto;
}

.tool-output__markdown :deep(code) {
  font-family: Consolas, Monaco, monospace;
}

.tool-output__markdown :deep(table) {
  border-collapse: collapse;
}

.tool-output__markdown :deep(th),
.tool-output__markdown :deep(td) {
  border: 1px solid var(--el-border-color);
  padding: 6px 10px;
}
</style>
