<script setup lang="ts">
/**
 * PostgreSQL introspection.
 *
 * Read-only: the statements are fixed in the backend repository and only their
 * `LIMIT` is bound as a parameter, so there is no SQL console here. A failing
 * collector produces a degraded reading, never an error page.
 */
import { computed, ref } from 'vue'
import { ElButton, ElDescriptions, ElDescriptionsItem, ElTable, ElTableColumn } from 'element-plus'

import {
  fetchDatabaseCache,
  fetchDatabaseConnections,
  fetchDatabaseLocks,
  fetchDatabaseOverview,
  fetchDatabaseSlowQueries,
  fetchDatabaseStorage,
  fetchDatabaseTransactions,
} from '@/api/ops/database'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ProbePanel from '@/components/common/ProbePanel.vue'
import StatCard from '@/components/charts/StatCard.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { formatBytes, formatCount, formatDateTime, formatDuration, formatPercent, orEmpty } from '@/utils/format'

interface Bundle {
  overview: Awaited<ReturnType<typeof fetchDatabaseOverview>>
  connections: Awaited<ReturnType<typeof fetchDatabaseConnections>>
  transactions: Awaited<ReturnType<typeof fetchDatabaseTransactions>>
  locks: Awaited<ReturnType<typeof fetchDatabaseLocks>>
  slowQueries: Awaited<ReturnType<typeof fetchDatabaseSlowQueries>>
  storage: Awaited<ReturnType<typeof fetchDatabaseStorage>>
  cache: Awaited<ReturnType<typeof fetchDatabaseCache>>
}

const limit = ref(20)

const bundle = useAsyncData<Bundle>(async () => {
  const [overview, connections, transactions, locks, slowQueries, storage, cache] =
    await Promise.all([
      fetchDatabaseOverview(),
      fetchDatabaseConnections(),
      fetchDatabaseTransactions(),
      fetchDatabaseLocks(limit.value),
      fetchDatabaseSlowQueries(limit.value),
      fetchDatabaseStorage(limit.value),
      fetchDatabaseCache(),
    ])
  return { overview, connections, transactions, locks, slowQueries, storage, cache }
})

const connectionStates = computed(() => bundle.data.value?.connections.states ?? [])
const slowest = computed(() => bundle.data.value?.slowQueries.slowest_statements ?? [])
const longRunning = computed(() => bundle.data.value?.slowQueries.long_running_queries ?? [])
const waitingSessions = computed(() => bundle.data.value?.locks.waiting_sessions ?? [])
const tables = computed(() => bundle.data.value?.storage.tables ?? [])
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="PostgreSQL" description="数据库实例的运行状况（只读采集）">
      <template #actions>
        <ElButton @click="bundle.reload()">刷新</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="bundle.loading.value"
      :failed="bundle.failed.value"
      :empty="bundle.data.value === null"
      :error="bundle.error.value"
      empty-text="未能采集到数据库指标"
      :skeleton-rows="6"
      @retry="bundle.reload()"
    >
      <ProbePanel title="实例概览" :reading="bundle.data.value?.overview ?? null">
        <div class="database__stats">
          <StatCard label="版本" :value="orEmpty(bundle.data.value?.overview.version)" />
          <StatCard label="连接数" :value="formatCount(bundle.data.value?.overview.connection_count)" />
          <StatCard
            label="缓存命中率"
            :value="formatPercent(bundle.data.value?.overview.cache_hit_ratio ?? 0)"
          />
          <StatCard
            label="库大小"
            :value="formatBytes(bundle.data.value?.overview.database_size_bytes)"
          />
          <StatCard
            label="运行时间"
            :value="formatDuration(bundle.data.value?.overview.uptime_seconds)"
          />
        </div>
      </ProbePanel>

      <ProbePanel title="连接" :reading="bundle.data.value?.connections ?? null">
        <div class="database__grid">
          <ElDescriptions :column="1" border size="small">
            <ElDescriptionsItem label="当前连接">
              {{ formatCount(bundle.data.value?.connections.total) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="最大连接">
              {{ formatCount(bundle.data.value?.connections.max_connections) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="使用率">
              {{ formatPercent(bundle.data.value?.connections.utilization_ratio ?? 0) }}
            </ElDescriptionsItem>
          </ElDescriptions>
          <ElTable :data="connectionStates" size="small">
            <ElTableColumn prop="state" label="状态" min-width="160" />
            <ElTableColumn label="数量" width="100">
              <template #default="{ row }">{{ formatCount(row.count) }}</template>
            </ElTableColumn>
            <template #empty><span class="vctn-muted">无连接状态</span></template>
          </ElTable>
        </div>
      </ProbePanel>

      <ProbePanel title="事务" :reading="bundle.data.value?.transactions ?? null">
        <div class="database__stats">
          <StatCard label="提交" :value="formatCount(bundle.data.value?.transactions.commits)" />
          <StatCard label="回滚" :value="formatCount(bundle.data.value?.transactions.rollbacks)" />
          <StatCard label="死锁" :value="formatCount(bundle.data.value?.transactions.deadlocks)" />
          <StatCard
            label="回滚率"
            :value="formatPercent(bundle.data.value?.transactions.rollback_ratio ?? 0)"
          />
        </div>
      </ProbePanel>

      <ProbePanel title="锁" :reading="bundle.data.value?.locks ?? null">
        <div class="database__stats">
          <StatCard label="总锁数" :value="formatCount(bundle.data.value?.locks.total_locks)" />
          <StatCard label="已授予" :value="formatCount(bundle.data.value?.locks.granted_locks)" />
          <StatCard label="等待中" :value="formatCount(bundle.data.value?.locks.waiting_locks)" />
        </div>
        <ElTable :data="waitingSessions" size="small" class="database__table">
          <ElTableColumn prop="pid" label="PID" width="90" />
          <ElTableColumn prop="database_name" label="数据库" min-width="140" />
          <ElTableColumn prop="wait_event_type" label="等待类型" min-width="140" />
          <ElTableColumn prop="wait_event" label="等待事件" min-width="160" />
          <ElTableColumn label="等待时长" width="120">
            <template #default="{ row }">{{ formatDuration(row.wait_seconds) }}</template>
          </ElTableColumn>
          <template #empty><span class="vctn-muted">没有等待锁的会话</span></template>
        </ElTable>
      </ProbePanel>

      <ProbePanel title="慢查询" :reading="bundle.data.value?.slowQueries ?? null">
        <p v-if="!bundle.data.value?.slowQueries.statements_extension_available" class="vctn-muted">
          未安装 pg_stat_statements 扩展，仅展示当前长时间运行的查询。
        </p>
        <ElTable :data="slowest" size="small" class="database__table">
          <ElTableColumn label="调用次数" width="110">
            <template #default="{ row }">{{ formatCount(row.calls) }}</template>
          </ElTableColumn>
          <ElTableColumn label="平均耗时 (ms)" width="130">
            <template #default="{ row }">{{ orEmpty(row.mean_ms) }}</template>
          </ElTableColumn>
          <ElTableColumn label="最大耗时 (ms)" width="130">
            <template #default="{ row }">{{ orEmpty(row.max_ms) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="statement" label="语句" min-width="260" show-overflow-tooltip />
          <template #empty><span class="vctn-muted">无慢查询统计</span></template>
        </ElTable>

        <ElTable :data="longRunning" size="small" class="database__table">
          <ElTableColumn prop="pid" label="PID" width="90" />
          <ElTableColumn prop="database_name" label="数据库" min-width="140" />
          <ElTableColumn prop="wait_event_type" label="等待类型" min-width="140" />
          <ElTableColumn label="已运行时长" width="130">
            <template #default="{ row }">{{ formatDuration(row.duration_seconds) }}</template>
          </ElTableColumn>
          <template #empty><span class="vctn-muted">没有长时间运行的查询</span></template>
        </ElTable>
      </ProbePanel>

      <ProbePanel title="存储" :reading="bundle.data.value?.storage ?? null">
        <ElTable :data="tables" size="small">
          <ElTableColumn prop="schema_name" label="Schema" width="120" />
          <ElTableColumn prop="table_name" label="表" min-width="180" />
          <ElTableColumn label="总大小" width="120">
            <template #default="{ row }">{{ formatBytes(row.total_bytes) }}</template>
          </ElTableColumn>
          <ElTableColumn label="索引大小" width="120">
            <template #default="{ row }">{{ formatBytes(row.index_bytes) }}</template>
          </ElTableColumn>
          <ElTableColumn label="存活行数" width="120">
            <template #default="{ row }">{{ formatCount(row.live_rows) }}</template>
          </ElTableColumn>
          <template #empty><span class="vctn-muted">无表统计</span></template>
        </ElTable>
      </ProbePanel>

      <ProbePanel title="缓存" :reading="bundle.data.value?.cache ?? null">
        <div class="database__stats">
          <StatCard label="命中块" :value="formatCount(bundle.data.value?.cache.blocks_hit)" />
          <StatCard label="读取块" :value="formatCount(bundle.data.value?.cache.blocks_read)" />
          <StatCard label="命中率" :value="formatPercent(bundle.data.value?.cache.hit_ratio ?? 0)" />
        </div>
      </ProbePanel>

      <p class="vctn-muted">
        采集时间基准：{{ formatDateTime(bundle.data.value?.overview.collected_at) }}
      </p>
    </DataStateView>
  </div>
</template>

<style scoped>
.database__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--vctn-space-4);
}

.database__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--vctn-space-4);
  align-items: start;
}

.database__table {
  margin-top: var(--vctn-space-3);
}
</style>
