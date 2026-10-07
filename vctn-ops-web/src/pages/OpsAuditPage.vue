<script setup lang="ts">
/**
 * The ops audit trail.
 *
 * Append-only and read-only: every write in this console is recorded by the
 * backend, and the record — including what changed — is what an incident review
 * reads afterwards. The before/after payloads are shown as JSON because their
 * shape depends on the resource.
 */
import { ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElTableColumn,
} from 'element-plus'

import { listAuditRecords } from '@/api/ops/audit'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import type { OpsAuditRecord } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'

const filters = ref({
  action: '',
  resourceType: '',
  operatorUsername: '',
  result: '',
  traceId: '',
  range: null as [string, string] | null,
})

const list = usePagedList<OpsAuditRecord>((page, pageSize) =>
  listAuditRecords(page, pageSize, {
    action: filters.value.action.trim() === '' ? undefined : filters.value.action.trim(),
    resourceType:
      filters.value.resourceType.trim() === '' ? undefined : filters.value.resourceType.trim(),
    operatorUsername:
      filters.value.operatorUsername.trim() === '' ? undefined : filters.value.operatorUsername.trim(),
    result: filters.value.result === '' ? undefined : filters.value.result,
    traceId: filters.value.traceId.trim() === '' ? undefined : filters.value.traceId.trim(),
    startAt: filters.value.range?.[0] ?? null,
    endAt: filters.value.range?.[1] ?? null,
  }),
)

void list.reload()

const detailVisible = ref(false)
const detail = ref<OpsAuditRecord | null>(null)

function openDetail(row: OpsAuditRecord): void {
  detail.value = row
  detailVisible.value = true
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="运维审计" description="运维写操作的完整留痕（只读）" />

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput v-model="filters.action" placeholder="动作" clearable class="audit__field" />
        <ElInput v-model="filters.resourceType" placeholder="资源类型" clearable class="audit__field" />
        <ElInput
          v-model="filters.operatorUsername"
          placeholder="操作人"
          clearable
          class="audit__field"
        />
        <ElInput v-model="filters.result" placeholder="结果" clearable class="audit__field" />
        <ElInput
          v-model="filters.traceId"
          placeholder="Trace ID"
          clearable
          class="audit__trace"
          @keyup.enter="list.search()"
        />
        <ElDatePicker
          v-model="filters.range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="audit__range"
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
      empty-text="没有审计记录"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn label="时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="操作人" width="130">
        <template #default="{ row }">{{ orEmpty(row.operator_username) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="action" label="动作" width="160" />
      <ElTableColumn prop="resource_type" label="资源类型" width="140" />
      <ElTableColumn label="资源 ID" width="140">
        <template #default="{ row }">{{ orEmpty(row.resource_id) }}</template>
      </ElTableColumn>
      <ElTableColumn label="结果" width="100">
        <template #default="{ row }"><StatusTag :value="row.result" /></template>
      </ElTableColumn>
      <ElTableColumn prop="error_message" label="错误" min-width="180" show-overflow-tooltip />

      <template #operations="{ row }">
        <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="detailVisible" title="审计详情" width="720">
      <ElDescriptions v-if="detail" :column="2" border size="small">
        <ElDescriptionsItem label="时间">{{ formatDateTime(detail.created_at) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="操作人">{{ orEmpty(detail.operator_username) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="动作">{{ detail.action }}</ElDescriptionsItem>
        <ElDescriptionsItem label="结果">
          <StatusTag :value="detail.result" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="资源">{{ detail.resource_type }}</ElDescriptionsItem>
        <ElDescriptionsItem label="资源 ID">{{ orEmpty(detail.resource_id) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="IP">{{ orEmpty(detail.ip_address) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Trace ID">{{ orEmpty(detail.trace_id) }}</ElDescriptionsItem>
        <ElDescriptionsItem label="错误">{{ orEmpty(detail.error_message) }}</ElDescriptionsItem>
      </ElDescriptions>

      <template v-if="detail?.before_data">
        <h4 class="audit__json-title">变更前</h4>
        <pre class="audit__json">{{ JSON.stringify(detail.before_data, null, 2) }}</pre>
      </template>
      <template v-if="detail?.after_data">
        <h4 class="audit__json-title">变更后</h4>
        <pre class="audit__json">{{ JSON.stringify(detail.after_data, null, 2) }}</pre>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.audit__field {
  width: 140px;
}

.audit__trace {
  width: 180px;
}

.audit__range {
  width: 340px;
}

.audit__json-title {
  margin: var(--vctn-space-4) 0 var(--vctn-space-2);
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-base);
  font-weight: 500;
}

.audit__json {
  margin: 0;
  padding: var(--vctn-space-3);
  border-radius: var(--vctn-radius-md);
  background-color: var(--vctn-bg-inset);
  font-family: var(--vctn-font-mono);
  font-size: var(--vctn-text-xs);
  overflow-x: auto;
}
</style>
