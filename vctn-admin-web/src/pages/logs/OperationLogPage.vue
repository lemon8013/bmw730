<script setup lang="ts">
/** 操作日志：记录业务操作及其实施者，支持按操作与资源检索。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElOption,
  ElSelect,
  ElTableColumn,
} from 'element-plus'

import { listOperationLogs } from '@/api/audit'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import type { OperationLog, OperationLogQuery } from '@/types/audit'
import { RESULT_LABEL, RESULT_VALUE } from '@/types/enums'
import { formatDateTime } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.operationLogView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toOperationLog(row: Record<string, unknown>): OperationLog {
  return row as unknown as OperationLog
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  operation: string
  operator_id: string
  resource_type: string
  result: string
  dateRange: [string, string] | null
}>({ operation: '', operator_id: '', resource_type: '', result: '', dateRange: null })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): OperationLogQuery {
  const range = filters.dateRange
  return {
    operation: filters.operation.trim() === '' ? undefined : filters.operation.trim(),
    operator_id: filters.operator_id.trim() === '' ? undefined : filters.operator_id.trim(),
    resource_type: filters.resource_type.trim() === '' ? undefined : filters.resource_type.trim(),
    result: filters.result === '' ? undefined : filters.result,
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() => listOperationLogs(buildQuery()))

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

function search(): void {
  changePage(1)
  void reload()
}

function resetFilters(): void {
  filters.operation = ''
  filters.operator_id = ''
  filters.resource_type = ''
  filters.result = ''
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailLog = ref<OperationLog | null>(null)

function openDetail(row: Record<string, unknown>): void {
  detailLog.value = toOperationLog(row)
  detailVisible.value = true
}
</script>

<template>
  <div class="operation-log-page">
    <PageHeader title="操作日志" description="记录业务操作、实施者与目标资源，用于追溯管理动作。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无操作日志"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #toolbar>
          <div class="log-filters">
            <div class="log-filters__row">
              <ElInput
                v-model="filters.operation"
                class="log-filters__field"
                placeholder="操作名"
                clearable
                @keyup.enter="search"
              />
              <ElInput
                v-model="filters.operator_id"
                class="log-filters__field"
                placeholder="操作人 ID"
                clearable
                @keyup.enter="search"
              />
              <ElInput
                v-model="filters.resource_type"
                class="log-filters__field"
                placeholder="资源类型"
                clearable
                @keyup.enter="search"
              />
              <ElSelect
                v-model="filters.result"
                class="log-filters__field"
                placeholder="结果"
                clearable
              >
                <ElOption
                  v-for="item in RESULT_VALUE"
                  :key="item"
                  :label="RESULT_LABEL[item]"
                  :value="item"
                />
              </ElSelect>
              <div class="log-filters__field log-filters__field--range">
                <span class="log-filters__label">时间范围</span>
                <ElDatePicker
                  v-model="filters.dateRange"
                  class="log-filters__range"
                  type="datetimerange"
                  range-separator="至"
                  start-placeholder="开始时间"
                  end-placeholder="结束时间"
                  format="YYYY-MM-DD HH:mm:ss"
                  value-format="YYYY-MM-DD HH:mm:ss"
                  unlink-panels
                  clearable
                />
              </div>
              <div class="log-filters__actions">
                <ElButton type="primary" @click="search">查询</ElButton>
                <ElButton @click="resetFilters">重置</ElButton>
              </div>
            </div>
          </div>
        </template>
        <ElTableColumn
          v-if="!fields.isHidden('operation')"
          prop="operation"
          label="操作"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('operator_id')"
          prop="operator_id"
          label="操作人 ID"
          min-width="120"
        />
        <ElTableColumn
          v-if="!fields.isHidden('resource_type')"
          prop="resource_type"
          label="资源类型"
          min-width="120"
        />
        <ElTableColumn
          v-if="!fields.isHidden('resource_id')"
          prop="resource_id"
          label="资源 ID"
          min-width="120"
        />
        <ElTableColumn v-if="!fields.isHidden('result')" label="结果" width="96">
          <template #default="{ row }">
            <StatusTag :value="row.result" :labels="RESULT_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog v-model="detailVisible" title="操作日志详情" width="720px" hide-footer>
      <ElDescriptions v-if="detailLog" :column="2" border>
        <ElDescriptionsItem v-if="!fields.isHidden('operation')" label="操作">
          {{ detailLog.operation }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('operator_id')" label="操作人 ID">
          {{ detailLog.operator_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('resource_type')" label="资源类型">
          {{ detailLog.resource_type ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('resource_id')" label="资源 ID">
          {{ detailLog.resource_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('result')" label="结果">
          <StatusTag :value="detailLog.result" :labels="RESULT_LABEL" />
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('trace_id')" label="Trace ID">
          {{ detailLog.trace_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('created_at')" label="时间">
          {{ formatDateTime(detailLog.created_at) }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div v-if="!fields.isHidden('metadata')" class="operation-log-page__section">
        <h4 class="operation-log-page__section-title">元数据（metadata）</h4>
        <JsonViewer :value="detailLog?.metadata ?? null" />
      </div>
    </BaseDialog>
  </div>
</template>

<style scoped>
.log-filters {
  width: 100%;
}

.log-filters__row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.log-filters__field {
  width: 200px;
}

.log-filters__field--range {
  display: flex;
  align-items: center;
  gap: 8px;
  width: auto;
}

.log-filters__label {
  color: var(--el-text-color-regular);
  font-size: 14px;
  white-space: nowrap;
}

.log-filters__range {
  width: 360px;
}

.log-filters__actions {
  display: flex;
  gap: 8px;
}

.operation-log-page__section {
  margin-top: 16px;
}

.operation-log-page__section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}
</style>
