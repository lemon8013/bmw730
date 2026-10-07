<script setup lang="ts">
/**
 * The unified log search.
 *
 * The four streams stay separate tables on the backend; this screen searches
 * them through one redacted shape, so nothing here can show a raw request or
 * response body — every metadata payload has already been sanitised server
 * side.
 *
 * "查看上下文" reconstructs a trace across all four streams, which is the only
 * way to read an incident that spans an access record and an application error.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElDrawer,
  ElInput,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
} from 'element-plus'

import { fetchLogContext, searchLogs } from '@/api/ops/logs'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import { DEFAULT_LOG_TYPE, LOG_TYPE, LOG_TYPE_LABEL, type LogType } from '@/types/enums'
import type { LogEntry } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'

type Range = [Date, Date] | null

const filters = ref({
  logType: DEFAULT_LOG_TYPE as LogType,
  level: '',
  keyword: '',
  traceId: '',
  range: null as Range | null,
})

const list = usePagedList<LogEntry>((page, pageSize) =>
  searchLogs(page, pageSize, {
    logType: filters.value.logType,
    level: filters.value.level.trim() === '' ? undefined : filters.value.level.trim(),
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    traceId: filters.value.traceId.trim() === '' ? undefined : filters.value.traceId.trim(),
    startAt: filters.value.range?.[0] ?? null,
    endAt: filters.value.range?.[1] ?? null,
  }),
)

void list.reload()

/** The trace whose context is open in the drawer. */
const contextTraceId = ref<string | null>(null)
const contextVisible = ref(false)
const context = useAsyncData(() =>
  contextTraceId.value === null ? Promise.resolve(null) : fetchLogContext(contextTraceId.value),
)

const contextItems = computed(() => context.data.value?.items ?? [])

function openContext(row: LogEntry): void {
  if (row.trace_id === null) {
    return
  }
  contextTraceId.value = row.trace_id
  contextVisible.value = true
  void context.reload()
}

const detailVisible = ref(false)
const detail = ref<LogEntry | null>(null)

function openDetail(row: LogEntry): void {
  detail.value = row
  detailVisible.value = true
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="日志中心" description="访问 / 应用 / 安全 / 操作四类日志的统一检索" />

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElSelect v-model="filters.logType" class="logs__type">
          <ElOption
            v-for="type in LOG_TYPE"
            :key="type"
            :value="type"
            :label="LOG_TYPE_LABEL[type]"
          />
        </ElSelect>
        <ElInput v-model="filters.level" placeholder="级别" clearable class="logs__level" />
        <ElInput
          v-model="filters.keyword"
          placeholder="关键字"
          clearable
          class="logs__keyword"
          @keyup.enter="list.search()"
        />
        <ElInput
          v-model="filters.traceId"
          placeholder="Trace ID"
          clearable
          class="logs__trace"
          @keyup.enter="list.search()"
        />
        <ElDatePicker
          v-model="filters.range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="logs__range"
        />
      </div>
      <div class="vctn-toolbar__actions">
        <ElButton @click="list.search()">查询</ElButton>
        <ElButton @click="filters.range = null; filters.level = ''; list.search()">重置</ElButton>
      </div>
    </div>

    <BaseTable
      :rows="list.rows.value"
      :loading="list.loading.value"
      :failed="list.failed.value"
      :error="list.error.value"
      :total="list.total.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      empty-text="没有匹配的日志"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn label="时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="级别" width="100">
        <template #default="{ row }"><StatusTag :value="row.level" /></template>
      </ElTableColumn>
      <ElTableColumn label="结果" width="100">
        <template #default="{ row }"><StatusTag :value="row.result" /></template>
      </ElTableColumn>
      <ElTableColumn prop="summary" label="摘要" min-width="260" show-overflow-tooltip />
      <ElTableColumn label="方法 / 路径" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.method">{{ row.method }} {{ orEmpty(row.path) }}</span>
          <span v-else>{{ orEmpty(row.path) }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="状态码" width="100">
        <template #default="{ row }">
          <ElTag v-if="row.status_code !== null" size="small" effect="plain">
            {{ row.status_code }}
          </ElTag>
          <span v-else class="vctn-muted">—</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="耗时 (ms)" width="110">
        <template #default="{ row }">{{ orEmpty(row.duration_ms) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
        <ElButton
          link
          type="primary"
          :disabled="row.trace_id === null"
          @click="openContext(row)"
        >
          上下文
        </ElButton>
      </template>
    </BaseTable>

    <ElDrawer v-model="contextVisible" :title="`Trace 上下文 · ${contextTraceId ?? ''}`" size="60%">
      <p v-if="context.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="context.failed.value" class="vctn-muted">
        {{ context.error.value ?? '加载失败' }}
      </p>
      <ElTable v-else :data="contextItems" size="small">
        <ElTableColumn label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="流" width="120">
          <template #default="{ row }">
            <ElTag size="small" effect="light">{{ row.log_type }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="级别" width="100">
          <template #default="{ row }"><StatusTag :value="row.level" /></template>
        </ElTableColumn>
        <ElTableColumn prop="summary" label="摘要" min-width="240" show-overflow-tooltip />
        <template #empty><span class="vctn-muted">该 Trace 没有其他记录</span></template>
      </ElTable>
    </ElDrawer>

    <ElDialog v-model="detailVisible" title="日志详情" width="720">
      <ElDescriptions v-if="detail" :column="2" border size="small">
        <ElDescriptionsItem label="类型">{{ detail.log_type }}</ElDescriptionsItem>
        <ElDescriptionsItem label="ID">{{ detail.id }}</ElDescriptionsItem>
        <ElDescriptionsItem label="时间">{{ formatDateTime(detail.created_at) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="级别">{{ orEmpty(detail.level) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="结果">{{ orEmpty(detail.result) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Trace ID">{{ orEmpty(detail.trace_id) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="IP">{{ orEmpty(detail.ip) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="摘要" :span="2">{{ detail.summary }}</ElDescriptionsItem>
        <ElDescriptionsItem label="异常类型">{{ orEmpty(detail.exception_type) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="错误码">{{ orEmpty(detail.error_code) }}</ElDescriptionsItem>
      </ElDescriptions>
      <pre v-if="detail?.metadata" class="logs__metadata">{{
        JSON.stringify(detail.metadata, null, 2)
      }}</pre>
    </ElDialog>
  </div>
</template>

<style scoped>
.logs__type {
  width: 140px;
}

.logs__level {
  width: 110px;
}

.logs__keyword {
  width: 180px;
}

.logs__trace {
  width: 200px;
}

.logs__range {
  width: 360px;
}

.logs__metadata {
  margin: var(--vctn-space-3) 0 0;
  padding: var(--vctn-space-3);
  border-radius: var(--vctn-radius-md);
  background-color: var(--vctn-bg-inset);
  font-family: var(--vctn-font-mono);
  font-size: var(--vctn-text-xs);
  overflow-x: auto;
}
</style>
