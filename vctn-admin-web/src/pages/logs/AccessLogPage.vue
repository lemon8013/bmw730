<script setup lang="ts">
/** 访问日志：HTTP 请求方法、路径、状态码与耗时。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElTableColumn,
  ElTag,
} from 'element-plus'

import { listAccessLogs } from '@/api/audit'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import type { AccessLog, AccessLogQuery } from '@/types/audit'
import { formatDateTime, formatDuration } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.accessLogView)

/** 常用 HTTP 方法，仅用于筛选下拉。 */
const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'] as const

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toAccessLog(row: Record<string, unknown>): AccessLog {
  return row as unknown as AccessLog
}

/** 状态码标签：2xx 成功、4xx 警告、其余危险。 */
function statusType(status: unknown): 'success' | 'warning' | 'danger' {
  if (typeof status !== 'number') {
    return 'danger'
  }
  if (status >= 200 && status < 400) {
    return 'success'
  }
  if (status >= 400 && status < 500) {
    return 'warning'
  }
  return 'danger'
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  method: string
  path: string
  status_code: number | undefined
  user_id: string
  dateRange: [string, string] | null
}>({ method: '', path: '', status_code: undefined, user_id: '', dateRange: null })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): AccessLogQuery {
  const range = filters.dateRange
  return {
    method: filters.method === '' ? undefined : filters.method,
    path: filters.path.trim() === '' ? undefined : filters.path.trim(),
    status_code: filters.status_code,
    user_id: filters.user_id.trim() === '' ? undefined : filters.user_id.trim(),
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() => listAccessLogs(buildQuery()))

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
  filters.method = ''
  filters.path = ''
  filters.status_code = undefined
  filters.user_id = ''
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailLog = ref<AccessLog | null>(null)

function openDetail(row: Record<string, unknown>): void {
  detailLog.value = toAccessLog(row)
  detailVisible.value = true
}
</script>

<template>
  <div class="access-log-page">
    <PageHeader title="访问日志" description="记录每一次 HTTP 请求的方法、路径、状态码与耗时。">
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
        empty-text="暂无访问日志"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #toolbar>
          <div class="log-filters">
            <div class="log-filters__row">
              <ElSelect
                v-model="filters.method"
                class="log-filters__field"
                placeholder="请求方法"
                clearable
              >
                <ElOption v-for="item in HTTP_METHODS" :key="item" :label="item" :value="item" />
              </ElSelect>
              <ElInput
                v-model="filters.path"
                class="log-filters__field"
                placeholder="请求路径"
                clearable
                @keyup.enter="search"
              />
              <ElInputNumber
                v-model="filters.status_code"
                class="log-filters__field"
                :min="100"
                :max="599"
                :controls="false"
                placeholder="状态码"
              />
              <ElInput
                v-model="filters.user_id"
                class="log-filters__field"
                placeholder="用户 ID"
                clearable
                @keyup.enter="search"
              />
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
        <ElTableColumn v-if="!fields.isHidden('method')" prop="method" label="方法" width="92" />
        <ElTableColumn v-if="!fields.isHidden('path')" prop="path" label="路径" min-width="220" />
        <ElTableColumn v-if="!fields.isHidden('status_code')" label="状态码" width="100">
          <template #default="{ row }">
            <ElTag :type="statusType(row.status_code)" size="small" disable-transitions>
              {{ row.status_code ?? '—' }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('ip')" prop="ip" label="IP" min-width="140" />
        <ElTableColumn
          v-if="!fields.isHidden('user_id')"
          prop="user_id"
          label="用户 ID"
          min-width="120"
        />
        <ElTableColumn v-if="!fields.isHidden('duration_ms')" label="耗时" width="110">
          <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
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

    <BaseDialog v-model="detailVisible" title="访问日志详情" width="720px" hide-footer>
      <ElDescriptions v-if="detailLog" :column="2" border>
        <ElDescriptionsItem v-if="!fields.isHidden('method')" label="方法">
          {{ detailLog.method }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('status_code')" label="状态码">
          {{ detailLog.status_code ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('path')" label="路径" :span="2">
          {{ detailLog.path }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('ip')" label="IP">
          {{ detailLog.ip ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('user_id')" label="用户 ID">
          {{ detailLog.user_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('duration_ms')" label="耗时">
          {{ formatDuration(detailLog.duration_ms) }}
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
</style>
