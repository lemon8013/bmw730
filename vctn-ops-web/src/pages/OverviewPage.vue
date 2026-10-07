<script setup lang="ts">
/**
 * Operations overview.
 *
 * The endpoint is total by contract: a counter is `0` and a list is empty when
 * there is no data, never `null` and never an error — so an empty monitoring
 * installation still renders instead of showing a failure.
 */
import { computed, ref } from 'vue'
import { ElButton, ElOption, ElSelect, ElTable, ElTableColumn } from 'element-plus'
import { useRouter } from 'vue-router'

import { fetchOverview } from '@/api/ops/dashboard'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/charts/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { ALERT_SEVERITY } from '@/types/enums'
import { formatDateTime, formatPercent } from '@/utils/format'

const router = useRouter()

const availabilityHours = ref(24)
const recentEventLimit = ref(10)

const overview = useAsyncData(() =>
  fetchOverview(availabilityHours.value, recentEventLimit.value),
)

const severityRows = computed(() =>
  ALERT_SEVERITY.map((severity) => ({
    severity,
    count: overview.data.value?.alerts_by_severity?.[severity] ?? 0,
  })),
)

const recentEvents = computed(() => overview.data.value?.recent_events ?? [])

const isEmpty = computed(() => overview.data.value === null)
</script>

<template>
  <div class="vctn-page">
    <PageHeader
      title="运维总览"
      description="主机、服务、告警、Agent 与可用性的当前快照"
    >
      <template #actions>
        <ElSelect v-model="availabilityHours" class="overview__select" @change="overview.reload()">
          <ElOption :value="24" label="近 24 小时" />
          <ElOption :value="72" label="近 3 天" />
          <ElOption :value="168" label="近 7 天" />
        </ElSelect>
        <ElButton @click="overview.reload()">刷新</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="overview.loading.value"
      :failed="overview.failed.value"
      :empty="isEmpty"
      :error="overview.error.value"
      empty-text="暂无总览数据"
      @retry="overview.reload()"
    >
      <div class="overview__stats">
        <StatCard
          label="主机"
          :value="`${overview.data.value?.online_host_count ?? 0} / ${overview.data.value?.host_count ?? 0}`"
          hint="在线 / 总数"
        />
        <StatCard
          label="服务"
          :value="`${overview.data.value?.abnormal_service_count ?? 0} / ${overview.data.value?.service_count ?? 0}`"
          hint="异常 / 总数"
        />
        <StatCard
          label="活跃告警"
          :value="overview.data.value?.active_alert_count ?? 0"
          hint="待认领或告警中"
        />
        <StatCard
          label="在线 Agent"
          :value="overview.data.value?.agent_online_count ?? 0"
          hint="最近心跳在窗口内"
        />
        <StatCard
          label="可用性成功率"
          :value="formatPercent(overview.data.value?.availability_success_rate ?? 0)"
          :hint="`${overview.data.value?.availability_check_count ?? 0} 次探测`"
        />
      </div>

      <div class="vctn-panel">
        <h3 class="vctn-section-title">告警按级别</h3>
        <div class="overview__severity">
          <div v-for="row in severityRows" :key="row.severity" class="overview__severity-item">
            <StatusTag :value="row.severity" />
            <span class="overview__severity-count">{{ row.count }}</span>
          </div>
        </div>
      </div>

      <div class="vctn-panel vctn-panel--flush">
        <div class="overview__events-header">
          <h3 class="vctn-section-title">最近事件</h3>
          <ElButton link type="primary" @click="router.push({ name: 'ops-events' })">
            查看全部
          </ElButton>
        </div>
        <ElTable :data="recentEvents" class="overview__table">
          <ElTableColumn prop="event_type" label="类型" width="160" />
          <ElTableColumn prop="source" label="来源" width="140" />
          <ElTableColumn label="级别" width="100">
            <template #default="{ row }">
              <StatusTag :value="row.severity" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="message" label="消息" min-width="240" show-overflow-tooltip />
          <ElTableColumn label="发生时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
          </ElTableColumn>
          <template #empty>
            <span class="vctn-muted">窗口内没有事件</span>
          </template>
        </ElTable>
      </div>
    </DataStateView>
  </div>
</template>

<style scoped>
.overview__select {
  width: 140px;
}

.overview__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--vctn-space-4);
}

.overview__severity {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-4);
}

.overview__severity-item {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-2);
}

.overview__severity-count {
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-lg);
  font-variant-numeric: tabular-nums;
}

.overview__events-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--vctn-space-4) var(--vctn-space-4) 0;
}

.overview__table {
  width: 100%;
}
</style>
