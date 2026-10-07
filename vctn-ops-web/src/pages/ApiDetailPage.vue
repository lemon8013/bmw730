<script setup lang="ts">
/**
 * One monitored endpoint, with the metrics of the window the operator picks.
 *
 * The window is the caller's decision — the backend presets nothing — and an
 * endpoint with no samples inside it reports zeros rather than an error, so a
 * freshly registered endpoint does not read as broken.
 */
import { computed, ref } from 'vue'
import { ElButton, ElDescriptions, ElDescriptionsItem, ElOption, ElSelect } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { getEndpoint, getEndpointMetrics } from '@/api/ops/apis'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/charts/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { formatDateTime, formatCount, formatPercent, orEmpty } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const endpointId = computed(() => {
  const raw = route.params.endpointId
  return typeof raw === 'string' ? raw : ''
})

const hours = ref(24)

const endpoint = useAsyncData(() => getEndpoint(endpointId.value))
const metrics = useAsyncData(() => getEndpointMetrics(endpointId.value, hours.value))
</script>

<template>
  <div class="vctn-page">
    <PageHeader
      :title="endpoint.data.value?.path_pattern || '端点详情'"
      :description="endpoint.data.value?.endpoint_key"
    >
      <template #actions>
        <ElButton @click="router.push({ name: 'ops-apis' })">返回列表</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="endpoint.loading.value"
      :failed="endpoint.failed.value"
      :empty="endpoint.data.value === null"
      :error="endpoint.error.value"
      empty-text="端点不存在或无权查看"
      @retry="endpoint.reload()"
    >
      <div class="vctn-panel">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="端点键">
            {{ endpoint.data.value?.endpoint_key }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="方法">
            <StatusTag :value="endpoint.data.value?.http_method ?? ''" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="路径">{{ endpoint.data.value?.path_pattern }}</ElDescriptionsItem>
          <ElDescriptionsItem label="环境">{{ endpoint.data.value?.environment }}</ElDescriptionsItem>
          <ElDescriptionsItem label="监控">
            <StatusTag
              :value="endpoint.data.value?.is_monitored ?? false"
              :boolean-labels="['未监控', '已监控']"
            />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="服务">
            {{ orEmpty(endpoint.data.value?.service_id) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="累计请求">
            {{ formatCount(endpoint.data.value?.request_count) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="累计错误">
            {{ formatCount(endpoint.data.value?.error_count) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="平均延迟 (ms)">
            {{ orEmpty(endpoint.data.value?.avg_latency_ms) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="P95 延迟 (ms)">
            {{ orEmpty(endpoint.data.value?.p95_latency_ms) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="最后出现">
            {{ formatDateTime(endpoint.data.value?.last_seen_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">
            {{ formatDateTime(endpoint.data.value?.created_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </div>
    </DataStateView>

    <div class="vctn-panel">
      <div class="api-detail__metrics-header">
        <h3 class="vctn-section-title">窗口指标</h3>
        <ElSelect v-model="hours" class="api-detail__hours" @change="metrics.reload()">
          <ElOption :value="1" label="近 1 小时" />
          <ElOption :value="24" label="近 24 小时" />
          <ElOption :value="72" label="近 3 天" />
          <ElOption :value="168" label="近 7 天" />
        </ElSelect>
      </div>

      <DataStateView
        :loading="metrics.loading.value"
        :failed="metrics.failed.value"
        :empty="metrics.data.value === null"
        :error="metrics.error.value"
        empty-text="窗口内没有采样"
        :skeleton-rows="2"
        @retry="metrics.reload()"
      >
        <div class="api-detail__stats">
          <StatCard label="请求数" :value="formatCount(metrics.data.value?.request_count)" />
          <StatCard label="错误数" :value="formatCount(metrics.data.value?.error_count)" />
          <StatCard label="错误率" :value="formatPercent(metrics.data.value?.error_rate ?? 0)" />
          <StatCard label="平均延迟 (ms)" :value="orEmpty(metrics.data.value?.avg_latency_ms)" />
          <StatCard label="P95 延迟 (ms)" :value="orEmpty(metrics.data.value?.p95_latency_ms)" />
          <StatCard
            label="采样点数"
            :value="formatCount(metrics.data.value?.sample_count)"
            :hint="`${formatDateTime(metrics.data.value?.window_start)} 起`"
          />
        </div>
      </DataStateView>
    </div>
  </div>
</template>

<style scoped>
.api-detail__metrics-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.api-detail__hours {
  width: 140px;
}

.api-detail__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--vctn-space-4);
}
</style>
