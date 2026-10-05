<script setup lang="ts">
/**
 * The console's one table.
 *
 * Bundles the four async states, an empty state, selection, pagination, the
 * backend's `page` / `page_size` contract and a per-table column preference,
 * so no list page has to re-implement them and none can render an infinite
 * spinner or a silently blank grid.
 *
 * Columns are discovered from the `ElTableColumn` children the page declares,
 * which means every table gets show/hide and reordering for free — a page only
 * has to declare its columns.
 */
import { computed, onMounted, ref, useSlots, type VNode } from 'vue'
import {
  ElAlert,
  ElButton,
  ElEmpty,
  ElIcon,
  ElPagination,
  ElPopover,
  ElTable,
  ElTableColumn,
} from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

import ColumnSettings from '@/components/table/ColumnSettings.vue'
import {
  applySettings,
  keyColumnNodes,
  loadTableSettings,
  reconcileSettings,
  saveTableSettings,
  tableKeyFromPath,
  type TableColumnMeta,
  type TableSettings,
} from '@/components/table/column-settings'
import { PAGE_SIZES } from '@/composables/usePagination'
import type { RenderedError } from '@/utils/error'

interface Props {
  /** Rows to render; the generic is intentionally structural. */
  rows: readonly Record<string, unknown>[]
  loading: boolean
  failed: boolean
  error?: RenderedError | null
  total: number
  page: number
  pageSize: number
  rowKey?: string
  emptyText?: string
  /** Show the selection column. */
  selectable?: boolean
  /** Show the pagination footer. */
  paginated?: boolean
  /**
   * Stable identity of this table's column preference. Defaults to the current
   * route path, which is unique per list page.
   */
  settingsKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  error: null,
  rowKey: 'id',
  emptyText: '暂无数据',
  selectable: false,
  paginated: true,
  settingsKey: undefined,
})

const emit = defineEmits<{
  retry: []
  'update:page': [value: number]
  'update:pageSize': [value: number]
  'selection-change': [rows: Record<string, unknown>[]]
}>()

const slots = useSlots()
const route = useRoute()

const resolvedKey = computed(() => props.settingsKey ?? tableKeyFromPath(route.path))

const settings = ref<TableSettings>({ order: [], hidden: [] })

/** Column metadata of the last render, for the settings panel. */
const panelColumns = ref<TableColumnMeta[]>([])

onMounted(() => {
  settings.value = loadTableSettings(resolvedKey.value)
})

function persist(next: TableSettings): void {
  settings.value = next
  saveTableSettings(resolvedKey.value, next)
}

/**
 * The table's default slot.
 *
 * Declared as a functional component so the columns can be reordered and
 * filtered before Element Plus collects them. `ElTableColumn` resolves its
 * owning table by walking up the component chain, so an extra wrapper between
 * the table and the columns is transparent to it.
 */
function TableColumns(): VNode[] {
  const declared = slots.default?.() ?? []
  const entries = keyColumnNodes(declared)
  const metas = entries.map((entry) => entry.meta)
  panelColumns.value = metas
  return applySettings(entries, reconcileSettings(metas, settings.value))
}

function onSettingsUpdate(next: TableSettings): void {
  persist(next)
}

function onPageChange(next: number): void {
  emit('update:page', next)
}

function onPageSizeChange(next: number): void {
  emit('update:pageSize', next)
}

function onSelectionChange(rows: Record<string, unknown>[]): void {
  emit('selection-change', rows)
}

/** Row key resolver: identifiers stay strings. */
function resolveRowKey(row: Record<string, unknown>): string {
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
      :description="error?.message ?? '请稍后重试'"
      class="base-table__alert"
    />

    <div v-if="failed" class="base-table__retry">
      <ElButton type="primary" @click="emit('retry')">重试</ElButton>
      <span v-if="error?.traceId" class="base-table__trace">Trace ID: {{ error.traceId }}</span>
    </div>

    <template v-else>
      <div class="base-table__toolbar">
        <div class="base-table__toolbar-slot">
          <slot name="toolbar" />
        </div>
        <ElPopover
          v-if="panelColumns.length > 0"
          trigger="click"
          placement="bottom-end"
          :width="280"
        >
          <template #reference>
            <ElButton size="small">
              <ElIcon><Setting /></ElIcon>
              <span class="base-table__settings-label">列设置</span>
            </ElButton>
          </template>
          <ColumnSettings
            :columns="panelColumns"
            :settings="settings"
            @update="onSettingsUpdate"
          />
        </ElPopover>
      </div>

      <ElTable
        v-loading="loading"
        :data="[...rows]"
        :row-key="resolveRowKey"
        border
        stripe
        class="base-table__table"
        @selection-change="onSelectionChange"
      >
        <ElTableColumn v-if="selectable" type="selection" width="48" reserve-selection />
        <TableColumns />
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
  margin-bottom: 12px;
}

.base-table__retry {
  display: flex;
  gap: 12px;
  align-items: center;
}

.base-table__trace {
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.base-table__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
  margin-bottom: 8px;
}

.base-table__toolbar-slot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.base-table__settings-label {
  margin-left: 4px;
}

.base-table__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
</style>
