<script setup lang="ts">
/** 审计日志：按条件检索、查看变更前后数据，并可跳转链路追踪。 */
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
} from 'element-plus'

import { listAuditLogs } from '@/api/audit'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import type { AuditLog, AuditLogQuery } from '@/types/audit'
import { RESULT_LABEL, RESULT_VALUE } from '@/types/enums'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.auditView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toAuditLog(row: Record<string, unknown>): AuditLog {
  return row as unknown as AuditLog
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  action: string
  operator_id: string
  resource_type: string
  resource_id: string
  result: string
  dateRange: [string, string] | null
}>({
  action: '',
  operator_id: '',
  resource_type: '',
  resource_id: '',
  result: '',
  dateRange: null,
})

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): AuditLogQuery {
  const range = filters.dateRange
  return {
    action: filters.action.trim() === '' ? undefined : filters.action.trim(),
    operator_id: filters.operator_id.trim() === '' ? undefined : filters.operator_id.trim(),
    resource_type: filters.resource_type.trim() === '' ? undefined : filters.resource_type.trim(),
    resource_id: filters.resource_id.trim() === '' ? undefined : filters.resource_id.trim(),
    result: filters.result === '' ? undefined : filters.result,
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() => listAuditLogs(buildQuery()))

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
  filters.action = ''
  filters.operator_id = ''
  filters.resource_type = ''
  filters.resource_id = ''
  filters.result = ''
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 详情与链路追踪
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailLog = ref<AuditLog | null>(null)
const detailTraceId = computed(() => detailLog.value?.trace_id ?? '')

function traceIdOf(row: Record<string, unknown>): string {
  const value = row.trace_id
  return typeof value === 'string' ? value : ''
}

function hasTrace(row: Record<string, unknown>): boolean {
  return traceIdOf(row) !== ''
}

function openDetail(row: Record<string, unknown>): void {
  detailLog.value = toAuditLog(row)
  detailVisible.value = true
}

function openTrace(traceId: string): void {
  if (traceId === '') {
    return
  }
  void router.push({ name: 'trace-detail', params: { traceId } })
}
</script>

<template>
  <div class="audit-log-page">
    <PageHeader title="审计日志" description="记录管理端写操作的变更前后数据，支持按操作人、资源与结果检索。">
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
        empty-text="暂无审计日志"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #toolbar>
          <div class="log-filters">
            <div class="log-filters__row">
              <ElInput
                v-model="filters.action"
                class="log-filters__field"
                placeholder="操作 action"
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
              <ElInput
                v-model="filters.resource_id"
                class="log-filters__field"
                placeholder="资源 ID"
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
          v-if="!fields.isHidden('operator_username')"
          prop="operator_username"
          label="操作人"
          min-width="140"
        />
        <ElTableColumn
          v-if="!fields.isHidden('action')"
          prop="action"
          label="操作"
          min-width="160"
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
        <ElTableColumn v-if="!fields.isHidden('ip')" prop="ip" label="IP" min-width="140" />
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <ElSpace>
              <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
              <ElButton
                v-if="hasTrace(row)"
                v-permission="PERMISSION.traceView"
                link
                type="primary"
                @click="openTrace(traceIdOf(row))"
              >
                查看链路
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog v-model="detailVisible" title="审计日志详情" width="760px" hide-footer>
      <ElDescriptions v-if="detailLog" :column="2" border>
        <ElDescriptionsItem
          v-if="!fields.isHidden('operator_username')"
          label="操作人"
        >
          {{ detailLog.operator_username ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('action')" label="操作">
          {{ detailLog.action }}
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
        <ElDescriptionsItem v-if="!fields.isHidden('ip')" label="IP">
          {{ detailLog.ip ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('trace_id')" label="Trace ID">
          {{ detailLog.trace_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('created_at')" label="时间">
          {{ formatDateTime(detailLog.created_at) }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div v-if="detailTraceId" class="audit-log-page__trace-action">
        <ElButton v-permission="PERMISSION.traceView" type="primary" @click="openTrace(detailTraceId)">
          查看链路
        </ElButton>
      </div>

      <div v-if="!fields.isHidden('before_data')" class="audit-log-page__section">
        <h4 class="audit-log-page__section-title">变更前（before_data）</h4>
        <JsonViewer :value="detailLog?.before_data ?? null" />
      </div>

      <div v-if="!fields.isHidden('after_data')" class="audit-log-page__section">
        <h4 class="audit-log-page__section-title">变更后（after_data）</h4>
        <JsonViewer :value="detailLog?.after_data ?? null" />
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
  color: var(--vctn-text-regular);
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

.audit-log-page__section {
  margin-top: 16px;
}

.audit-log-page__section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 500;
}

.audit-log-page__trace-action {
  margin-top: 12px;
}
</style>
