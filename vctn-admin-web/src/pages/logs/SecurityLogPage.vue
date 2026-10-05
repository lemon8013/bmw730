<script setup lang="ts">
/** 安全日志：登录、鉴权等安全事件的检索与详情查看。 */
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

import { listSecurityLogs } from '@/api/audit'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import type { SecurityLog, SecurityLogQuery } from '@/types/audit'
import { RESULT_LABEL, RESULT_VALUE } from '@/types/enums'
import { formatDateTime } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.securityLogView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toSecurityLog(row: Record<string, unknown>): SecurityLog {
  return row as unknown as SecurityLog
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  event_type: string
  user_id: string
  result: string
  dateRange: [string, string] | null
}>({ event_type: '', user_id: '', result: '', dateRange: null })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): SecurityLogQuery {
  const range = filters.dateRange
  return {
    event_type: filters.event_type.trim() === '' ? undefined : filters.event_type.trim(),
    user_id: filters.user_id.trim() === '' ? undefined : filters.user_id.trim(),
    result: filters.result === '' ? undefined : filters.result,
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() => listSecurityLogs(buildQuery()))

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
  filters.event_type = ''
  filters.user_id = ''
  filters.result = ''
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailLog = ref<SecurityLog | null>(null)

function openDetail(row: Record<string, unknown>): void {
  detailLog.value = toSecurityLog(row)
  detailVisible.value = true
}
</script>

<template>
  <div class="security-log-page">
    <PageHeader title="安全日志" description="记录登录、鉴权与风控等安全事件，可按事件类型与用户检索。">
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
        empty-text="暂无安全日志"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #toolbar>
          <div class="log-filters">
            <div class="log-filters__row">
              <ElInput
                v-model="filters.event_type"
                class="log-filters__field"
                placeholder="事件类型"
                clearable
                @keyup.enter="search"
              />
              <ElInput
                v-model="filters.user_id"
                class="log-filters__field"
                placeholder="用户 ID"
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
          v-if="!fields.isHidden('event_type')"
          prop="event_type"
          label="事件类型"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('user_id')"
          prop="user_id"
          label="用户 ID"
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
        <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog v-model="detailVisible" title="安全日志详情" width="720px" hide-footer>
      <ElDescriptions v-if="detailLog" :column="2" border>
        <ElDescriptionsItem v-if="!fields.isHidden('event_type')" label="事件类型">
          {{ detailLog.event_type }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('user_id')" label="用户 ID">
          {{ detailLog.user_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('result')" label="结果">
          <StatusTag :value="detailLog.result" :labels="RESULT_LABEL" />
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('error_code')" label="错误码">
          {{ detailLog.error_code ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('ip')" label="IP">
          {{ detailLog.ip ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('trace_id')" label="Trace ID">
          {{ detailLog.trace_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('user_agent')" label="User Agent" :span="2">
          {{ detailLog.user_agent ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('created_at')" label="时间">
          {{ formatDateTime(detailLog.created_at) }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div v-if="!fields.isHidden('metadata')" class="security-log-page__section">
        <h4 class="security-log-page__section-title">元数据（metadata）</h4>
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

.security-log-page__section {
  margin-top: 16px;
}

.security-log-page__section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}
</style>
