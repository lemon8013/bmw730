<script setup lang="ts">
/** 链路追踪：按 Trace ID 汇总审计、安全、操作与访问四路日志。 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ElButton,
  ElCard,
  ElInput,
  ElSpace,
  ElTimeline,
  ElTimelineItem,
} from 'element-plus'

import { getTrace } from '@/api/traces'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/charts/StatCard.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type { TraceDetail } from '@/types/audit'
import { LOG_TYPE_LABEL } from '@/types/enums'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.traceView)

const routeTraceId = typeof route.params.traceId === 'string' ? route.params.traceId : ''
const inputTraceId = ref(routeTraceId)
const loadedTraceId = ref(routeTraceId)

const { data, loading, failed, error, reload } = useAsyncData<TraceDetail | null>(
  () => (loadedTraceId.value === '' ? Promise.resolve(null) : getTrace(loadedTraceId.value)),
  { initial: null },
)

/** 时间线中的一条日志。 */
interface TraceStreamEntry {
  key: string
  stream: string
  action: string
  result: string
  createdAt: string
}

const entries = computed<TraceStreamEntry[]>(() => {
  const detail = data.value
  if (detail === null) {
    return []
  }
  const list: TraceStreamEntry[] = []
  for (const log of detail.audit_logs ?? []) {
    list.push({
      key: `audit-${log.id}`,
      stream: LOG_TYPE_LABEL.audit,
      action: log.action,
      result: log.result,
      createdAt: log.created_at,
    })
  }
  for (const log of detail.security_logs ?? []) {
    list.push({
      key: `security-${log.id}`,
      stream: LOG_TYPE_LABEL.security,
      action: log.event_type,
      result: log.result,
      createdAt: log.created_at,
    })
  }
  for (const log of detail.operation_logs ?? []) {
    list.push({
      key: `operation-${log.id}`,
      stream: LOG_TYPE_LABEL.operation,
      action: log.operation,
      result: log.result,
      createdAt: log.created_at,
    })
  }
  for (const log of detail.access_logs ?? []) {
    list.push({
      key: `access-${log.id}`,
      stream: LOG_TYPE_LABEL.access,
      action: `${log.method} ${log.path}`,
      result: String(log.status_code ?? '—'),
      createdAt: log.created_at,
    })
  }
  return list.sort((left, right) => left.createdAt.localeCompare(right.createdAt))
})

const counts = computed(() => ({
  audit: data.value?.audit_logs?.length ?? 0,
  security: data.value?.security_logs?.length ?? 0,
  operation: data.value?.operation_logs?.length ?? 0,
  access: data.value?.access_logs?.length ?? 0,
}))

const resolvedTraceId = computed(() => data.value?.trace_id ?? loadedTraceId.value)

function search(): void {
  const id = inputTraceId.value.trim()
  if (id === '') {
    notify.warning('请输入 Trace ID')
    return
  }
  loadedTraceId.value = id
  void router.replace({ name: 'trace-detail', params: { traceId: id } })
  void reload()
}

function reloadTrace(): void {
  if (loadedTraceId.value === '') {
    notify.warning('请输入 Trace ID')
    return
  }
  void reload()
}
</script>

<template>
  <div class="trace-page">
    <PageHeader
      title="链路追踪"
      description="根据 Trace ID 聚合展示一次请求在审计、安全、操作与访问日志中的全部记录。"
    >
      <template #actions>
        <ElButton @click="reloadTrace">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="trace-page__search">
      <ElSpace wrap>
        <ElInput
          v-model="inputTraceId"
          placeholder="请输入 Trace ID"
          clearable
          style="width: 360px"
          @keyup.enter="search"
        />
        <ElButton v-permission="PERMISSION.traceView" type="primary" @click="search">查询</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never">
      <DataStateView
        :loading="loading"
        :failed="failed"
        :error="error"
        :empty="loadedTraceId === '' || entries.length === 0"
        empty-text="暂无链路数据，请输入 Trace ID 查询或从日志页点击“查看链路”。"
        @retry="reload"
      >
        <div class="trace-page__summary">
          <StatCard label="Trace ID" :value="resolvedTraceId || '—'" />
          <StatCard label="审计日志" :value="counts.audit" />
          <StatCard label="安全日志" :value="counts.security" />
          <StatCard label="操作日志" :value="counts.operation" />
          <StatCard label="访问日志" :value="counts.access" />
        </div>

        <ElTimeline class="trace-page__timeline">
          <ElTimelineItem
            v-for="entry in entries"
            :key="entry.key"
            :timestamp="formatDateTime(entry.createdAt)"
            placement="top"
          >
            <p v-if="!fields.isHidden('stream')" class="trace-page__entry-stream">
              {{ entry.stream }}
            </p>
            <p v-if="!fields.isHidden('action')" class="trace-page__entry-action">
              {{ entry.action }}
            </p>
            <p v-if="!fields.isHidden('result')" class="trace-page__entry-result">
              结果：{{ entry.result }}
            </p>
          </ElTimelineItem>
        </ElTimeline>
      </DataStateView>
    </ElCard>
  </div>
</template>

<style scoped>
.trace-page__search {
  margin-bottom: 16px;
}

.trace-page__summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.trace-page__timeline {
  padding-left: 4px;
}

.trace-page__entry-stream {
  margin: 0;
  color: var(--vctn-text-secondary);
  font-size: 12px;
}

.trace-page__entry-action {
  margin: 4px 0 0;
  font-size: 14px;
  font-weight: 500;
  word-break: break-all;
}

.trace-page__entry-result {
  margin: 4px 0 0;
  font-size: 13px;
}
</style>
