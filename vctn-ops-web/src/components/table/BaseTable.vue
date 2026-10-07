<script setup lang="ts" generic="T">
/**
 * The console's one table.
 *
 * Bundles the four async states, an empty state, pagination and the backend's
 * `page` / `page_size` contract, so no list page has to re-implement them and
 * none can render an infinite spinner or a silently blank grid.
 */
import { computed } from 'vue'
import { ElAlert, ElButton, ElEmpty, ElPagination, ElTable, ElTableColumn } from 'element-plus'

import { PAGE_SIZES } from '@/composables/usePagination'

interface Props {
  /** Rows to render. The row type flows through to the `operations` slot. */
  rows: readonly T[]
  loading: boolean
  failed: boolean
  error?: string | null
  total: number
  page: number
  pageSize: number
  rowKey?: string
  emptyText?: string
  /** Show the pagination footer. */
  paginated?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  error: null,
  rowKey: 'id',
  emptyText: '暂无数据',
  paginated: true,
})

const emit = defineEmits<{
  retry: []
  'update:page': [value: number]
  'update:pageSize': [value: number]
}>()

/** Element Plus takes a loose row record; the page's row type is opaque here. */
const tableRows = computed(() => [...props.rows] as unknown as Record<PropertyKey, unknown>[])

defineSlots<{
  default?: () => unknown
  /** Row-level actions; `row` is the concrete row type, not a loose record. */
  operations?: (props: { row: T }) => unknown
}>()

function onPageChange(next: number): void {
  emit('update:page', next)
}

function onPageSizeChange(next: number): void {
  emit('update:pageSize', next)
}

/** Element Plus hands back a loose record; hand the page its own row type. */
function asRow(row: unknown): T {
  return row as T
}

/** Row key resolver: identifiers stay strings. */
function resolveRowKey(row: Record<PropertyKey, unknown>): string {
  const value = row[props.rowKey]
  return value === null || value === undefined ? '' : String(value)
}
</script>

<template>
  <div class="base-table">
    <ElAlert
      v-if="failed"
      type="error"
      :closable="false"
      show-icon
      title="加载失败"
      :description="error ?? '请稍后重试'"
      class="base-table__alert"
    />

    <div v-if="failed" class="base-table__retry">
      <ElButton type="primary" @click="emit('retry')">重试</ElButton>
    </div>

    <template v-else>
      <ElTable
        v-loading="loading"
        :data="tableRows"
        :row-key="resolveRowKey"
        border
        stripe
        class="base-table__table"
      >
        <slot />
        <ElTableColumn v-if="$slots.operations" label="操作" width="180" fixed="right">
          <template #default="scope">
            <slot name="operations" :row="asRow(scope.row)" />
          </template>
        </ElTableColumn>
        <template #empty>
          <ElEmpty :description="loading ? '加载中…' : emptyText" />
        </template>
      </ElTable>
    </template>

    <div v-if="paginated && !failed" class="base-table__footer">
      <ElPagination
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[...PAGE_SIZES]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="onPageChange"
        @size-change="onPageSizeChange"
      />
    </div>
  </div>
</template>

<style scoped>
.base-table__alert {
  margin-bottom: var(--vctn-space-3);
}

.base-table__retry {
  display: flex;
  gap: var(--vctn-space-3);
  align-items: center;
}

.base-table__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--vctn-space-4);
}
</style>
