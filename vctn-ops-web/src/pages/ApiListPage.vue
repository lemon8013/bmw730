<script setup lang="ts">
/**
 * Monitored API endpoints.
 *
 * A read-only domain: endpoints are produced by normalising access logs, so
 * there is nothing to create or edit by hand — only to inspect.
 */
import { ref } from 'vue'
import {
  ElButton,
  ElInput,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'
import { useRouter } from 'vue-router'

import { listEndpoints } from '@/api/ops/apis'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import type { MonitoredEndpoint } from '@/types/ops'
import { formatDateTime, formatCount, orEmpty } from '@/utils/format'

const router = useRouter()

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as const

const filters = ref({
  keyword: '',
  httpMethod: '',
  environment: '',
  isMonitored: undefined as boolean | undefined,
})

const list = usePagedList<MonitoredEndpoint>((page, pageSize) =>
  listEndpoints(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    httpMethod: filters.value.httpMethod === '' ? undefined : filters.value.httpMethod,
    environment: filters.value.environment === '' ? undefined : filters.value.environment,
    isMonitored: filters.value.isMonitored,
  }),
)

void list.reload()
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="API 监控" description="由访问日志归一化产出的被监控端点" />

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="路径 / 端点键"
          clearable
          class="apis__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.httpMethod" placeholder="方法" clearable class="apis__method">
          <ElOption v-for="method in HTTP_METHODS" :key="method" :value="method" :label="method" />
        </ElSelect>
        <ElInput v-model="filters.environment" placeholder="环境" clearable class="apis__env" />
        <span class="vctn-muted">仅看已监控</span>
        <ElSwitch v-model="filters.isMonitored" />
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
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn label="方法" width="90">
        <template #default="{ row }"><StatusTag :value="row.http_method" /></template>
      </ElTableColumn>
      <ElTableColumn prop="path_pattern" label="路径" min-width="260" show-overflow-tooltip />
      <ElTableColumn prop="environment" label="环境" width="110" />
      <ElTableColumn label="监控" width="90">
        <template #default="{ row }">
          <StatusTag :value="row.is_monitored" :boolean-labels="['未监控', '已监控']" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="请求数" width="120">
        <template #default="{ row }">{{ formatCount(row.request_count) }}</template>
      </ElTableColumn>
      <ElTableColumn label="错误数" width="110">
        <template #default="{ row }">{{ formatCount(row.error_count) }}</template>
      </ElTableColumn>
      <ElTableColumn label="平均延迟 (ms)" width="130">
        <template #default="{ row }">{{ orEmpty(row.avg_latency_ms) }}</template>
      </ElTableColumn>
      <ElTableColumn label="P95 (ms)" width="110">
        <template #default="{ row }">{{ orEmpty(row.p95_latency_ms) }}</template>
      </ElTableColumn>
      <ElTableColumn label="最后出现" width="180">
        <template #default="{ row }">{{ formatDateTime(row.last_seen_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton
          link
          type="primary"
          @click="router.push({ name: 'ops-api-detail', params: { endpointId: row.id } })"
        >
          详情
        </ElButton>
      </template>
    </BaseTable>
  </div>
</template>

<style scoped>
.apis__keyword {
  width: 220px;
}

.apis__method {
  width: 120px;
}

.apis__env {
  width: 130px;
}
</style>
