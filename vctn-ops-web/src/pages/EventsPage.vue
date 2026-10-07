<script setup lang="ts">
/** Operations events: everything the platform recorded happening. */
import { ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElInput,
  ElOption,
  ElSelect,
  ElTableColumn,
} from 'element-plus'

import { listEvents } from '@/api/ops/events'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { ALERT_SEVERITY } from '@/types/enums'
import type { OpsEvent } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'

const filters = ref({
  eventType: '',
  severity: '',
  source: '',
  traceId: '',
  range: null as [string, string] | null,
})

const list = usePagedList<OpsEvent>((page, pageSize) =>
  listEvents(page, pageSize, {
    eventType: filters.value.eventType.trim() === '' ? undefined : filters.value.eventType.trim(),
    severity: filters.value.severity === '' ? undefined : filters.value.severity,
    source: filters.value.source.trim() === '' ? undefined : filters.value.source.trim(),
    traceId: filters.value.traceId.trim() === '' ? undefined : filters.value.traceId.trim(),
    start: filters.value.range?.[0] ?? null,
    end: filters.value.range?.[1] ?? null,
  }),
)

void list.reload()
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="事件中心" description="运维事件的完整流水" />

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput v-model="filters.eventType" placeholder="事件类型" clearable class="events__field" />
        <ElSelect v-model="filters.severity" placeholder="级别" clearable class="events__field">
          <ElOption v-for="level in ALERT_SEVERITY" :key="level" :value="level" :label="level" />
        </ElSelect>
        <ElInput v-model="filters.source" placeholder="来源" clearable class="events__field" />
        <ElInput
          v-model="filters.traceId"
          placeholder="Trace ID"
          clearable
          class="events__trace"
          @keyup.enter="list.search()"
        />
        <ElDatePicker
          v-model="filters.range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="events__range"
        />
      </div>
      <div class="vctn-toolbar__actions">
        <ElButton @click="list.search()">查询</ElButton>
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
      empty-text="没有匹配的事件"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn label="发生时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="event_type" label="类型" width="150" />
      <ElTableColumn label="级别" width="100">
        <template #default="{ row }"><StatusTag :value="row.severity" /></template>
      </ElTableColumn>
      <ElTableColumn prop="source" label="来源" width="140" />
      <ElTableColumn prop="message" label="消息" min-width="260" show-overflow-tooltip />
      <ElTableColumn label="资源" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          {{ orEmpty(row.resource_type) }}<span v-if="row.resource_id"> / {{ row.resource_id }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="trace_id" label="Trace ID" min-width="200" show-overflow-tooltip />
    </BaseTable>
  </div>
</template>

<style scoped>
.events__field {
  width: 150px;
}

.events__trace {
  width: 200px;
}

.events__range {
  width: 360px;
}
</style>
