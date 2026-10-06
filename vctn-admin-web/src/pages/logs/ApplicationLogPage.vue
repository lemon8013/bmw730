<script setup lang="ts">
/** 应用日志：后端统一日志入口按 application 流检索。 */
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
  ElTag,
} from 'element-plus'

import { queryLogs } from '@/api/logs'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import type { AnyLogRow, ApplicationLog, UnifiedLogQuery } from '@/types/audit'
import { formatDateTime } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.logView)

/** 常用日志级别，仅用于筛选下拉。 */
const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const

/**
 * 统一日志接口返回的是联合类型；application 流具有 `level` 与 `message`
 * 两个字段，据此收窄为 {@link ApplicationLog}。
 */
function isApplicationLog(row: AnyLogRow): row is ApplicationLog {
  return 'level' in row && 'message' in row
}

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly ApplicationLog[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

/** 日志级别的标签配色。 */
function levelType(level: unknown): 'success' | 'info' | 'warning' | 'danger' {
  switch (level) {
    case 'DEBUG':
      return 'info'
    case 'INFO':
      return 'success'
    case 'WARNING':
      return 'warning'
    case 'ERROR':
    case 'CRITICAL':
      return 'danger'
    default:
      return 'info'
  }
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  level: string
  keyword: string
  dateRange: [string, string] | null
}>({ level: '', keyword: '', dateRange: null })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): UnifiedLogQuery {
  const range = filters.dateRange
  return {
    level: filters.level === '' ? undefined : filters.level,
    keyword: filters.keyword.trim() === '' ? undefined : filters.keyword.trim(),
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() =>
  queryLogs('application', buildQuery()),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const items = computed<ApplicationLog[]>(() =>
  (data.value?.items ?? []).filter(isApplicationLog),
)

const rows = computed(() => asRows(items.value))

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
  filters.level = ''
  filters.keyword = ''
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailLog = ref<ApplicationLog | null>(null)

function openDetail(row: Record<string, unknown>): void {
  detailLog.value = row as unknown as ApplicationLog
  detailVisible.value = true
}
</script>

<template>
  <div class="application-log-page">
    <PageHeader
      title="应用日志"
      description="通过统一日志接口（/admin/logs/application）检索应用运行日志。"
    >
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
        empty-text="暂无应用日志"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <template #toolbar>
          <div class="log-filters">
            <div class="log-filters__row">
              <ElSelect
                v-model="filters.level"
                class="log-filters__field"
                placeholder="日志级别"
                clearable
              >
                <ElOption v-for="item in LOG_LEVELS" :key="item" :label="item" :value="item" />
              </ElSelect>
              <ElInput
                v-model="filters.keyword"
                class="log-filters__field"
                placeholder="关键字（消息 / Logger）"
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
        <ElTableColumn v-if="!fields.isHidden('level')" label="级别" width="104">
          <template #default="{ row }">
            <ElTag :type="levelType(row.level)" size="small" disable-transitions>
              {{ row.level }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('logger_name')"
          prop="logger_name"
          label="Logger"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('message')"
          prop="message"
          label="消息"
          min-width="280"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('exception_type')"
          prop="exception_type"
          label="异常类型"
          min-width="160"
        />
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

    <BaseDialog v-model="detailVisible" title="应用日志详情" width="720px" hide-footer>
      <ElDescriptions v-if="detailLog" :column="2" border>
        <ElDescriptionsItem v-if="!fields.isHidden('level')" label="级别">
          <ElTag :type="levelType(detailLog.level)" size="small" disable-transitions>
            {{ detailLog.level }}
          </ElTag>
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('logger_name')" label="Logger">
          {{ detailLog.logger_name ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('message')" label="消息" :span="2">
          {{ detailLog.message }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('exception_type')" label="异常类型">
          {{ detailLog.exception_type ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('trace_id')" label="Trace ID">
          {{ detailLog.trace_id ?? '—' }}
        </ElDescriptionsItem>
        <ElDescriptionsItem v-if="!fields.isHidden('created_at')" label="时间">
          {{ formatDateTime(detailLog.created_at) }}
        </ElDescriptionsItem>
      </ElDescriptions>

      <div v-if="!fields.isHidden('metadata')" class="application-log-page__section">
        <h4 class="application-log-page__section-title">元数据（metadata）</h4>
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

.application-log-page__section {
  margin-top: 16px;
}

.application-log-page__section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 500;
}
</style>
