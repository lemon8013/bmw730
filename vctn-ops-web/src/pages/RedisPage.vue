<script setup lang="ts">
/**
 * Redis introspection.
 *
 * Read-only informational commands only (`PING` / `INFO` / `SLOWLOG LEN`). A
 * missing or unreachable cache degrades into a structured reading instead of an
 * error response, which is why every panel can say "采集失败" on its own.
 */
import { computed } from 'vue'
import { ElButton, ElDescriptions, ElDescriptionsItem, ElTable, ElTableColumn } from 'element-plus'

import {
  fetchRedisClients,
  fetchRedisKeyspace,
  fetchRedisMemory,
  fetchRedisOverview,
} from '@/api/ops/redis'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ProbePanel from '@/components/common/ProbePanel.vue'
import StatCard from '@/components/charts/StatCard.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { formatBytes, formatCount, formatDuration, formatPercent, orEmpty } from '@/utils/format'

interface Bundle {
  overview: Awaited<ReturnType<typeof fetchRedisOverview>>
  keyspace: Awaited<ReturnType<typeof fetchRedisKeyspace>>
  memory: Awaited<ReturnType<typeof fetchRedisMemory>>
  clients: Awaited<ReturnType<typeof fetchRedisClients>>
}

const bundle = useAsyncData<Bundle>(async () => {
  const [overview, keyspace, memory, clients] = await Promise.all([
    fetchRedisOverview(),
    fetchRedisKeyspace(),
    fetchRedisMemory(),
    fetchRedisClients(),
  ])
  return { overview, keyspace, memory, clients }
})

const databases = computed(() => bundle.data.value?.keyspace.databases ?? [])
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="Redis" description="缓存实例的运行状况（只读采集）">
      <template #actions>
        <ElButton @click="bundle.reload()">刷新</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="bundle.loading.value"
      :failed="bundle.failed.value"
      :empty="bundle.data.value === null"
      :error="bundle.error.value"
      empty-text="未能采集到 Redis 指标"
      :skeleton-rows="5"
      @retry="bundle.reload()"
    >
      <ProbePanel title="实例概览" :reading="bundle.data.value?.overview ?? null">
        <div class="redis__stats">
          <StatCard label="版本" :value="orEmpty(bundle.data.value?.overview.version)" />
          <StatCard label="角色" :value="orEmpty(bundle.data.value?.overview.role)" />
          <StatCard label="键总数" :value="formatCount(bundle.data.value?.overview.total_keys)" />
          <StatCard
            label="QPS"
            :value="formatCount(bundle.data.value?.overview.instantaneous_ops_per_sec)"
          />
          <StatCard
            label="命中率"
            :value="formatPercent(bundle.data.value?.overview.hit_ratio ?? 0)"
          />
          <StatCard
            label="运行时间"
            :value="formatDuration(bundle.data.value?.overview.uptime_seconds)"
          />
        </div>
      </ProbePanel>

      <ProbePanel title="键空间" :reading="bundle.data.value?.keyspace ?? null">
        <ElTable :data="databases" size="small">
          <ElTableColumn prop="name" label="库" min-width="120" />
          <ElTableColumn label="键数" width="120">
            <template #default="{ row }">{{ formatCount(row.keys) }}</template>
          </ElTableColumn>
          <ElTableColumn label="带 TTL" width="120">
            <template #default="{ row }">{{ orEmpty(row.expires) }}</template>
          </ElTableColumn>
          <ElTableColumn label="平均 TTL" width="120">
            <template #default="{ row }">{{ orEmpty(row.avg_ttl) }}</template>
          </ElTableColumn>
          <template #empty><span class="vctn-muted">没有持有键的数据库</span></template>
        </ElTable>
      </ProbePanel>

      <ProbePanel title="内存" :reading="bundle.data.value?.memory ?? null">
        <ElDescriptions :column="2" border size="small">
          <ElDescriptionsItem label="已用">
            {{ orEmpty(bundle.data.value?.memory.used_memory_human) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="峰值">
            {{ orEmpty(bundle.data.value?.memory.used_memory_peak_human) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="RSS">
            {{ formatBytes(bundle.data.value?.memory.used_memory_rss_bytes) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="上限">
            {{ formatBytes(bundle.data.value?.memory.max_memory_bytes) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="淘汰策略">
            {{ orEmpty(bundle.data.value?.memory.max_memory_policy) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="碎片率">
            {{ orEmpty(bundle.data.value?.memory.fragmentation_ratio) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="使用率">
            {{ formatPercent(bundle.data.value?.memory.utilization_ratio ?? 0) }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </ProbePanel>

      <ProbePanel title="客户端" :reading="bundle.data.value?.clients ?? null">
        <div class="redis__stats">
          <StatCard
            label="已连接"
            :value="formatCount(bundle.data.value?.clients.connected_clients)"
          />
          <StatCard
            label="阻塞中"
            :value="formatCount(bundle.data.value?.clients.blocked_clients)"
          />
          <StatCard label="最大连接" :value="formatCount(bundle.data.value?.clients.max_clients)" />
          <StatCard
            label="使用率"
            :value="formatPercent(bundle.data.value?.clients.utilization_ratio ?? 0)"
          />
        </div>
      </ProbePanel>
    </DataStateView>
  </div>
</template>

<style scoped>
.redis__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--vctn-space-4);
}
</style>
