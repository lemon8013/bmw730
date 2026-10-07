<script setup lang="ts">
/**
 * Operations reports.
 *
 * Every report is total by contract — no data yields zeros and empty rows
 * instead of an error — and the trend axis is dense: the backend sends every
 * day of the window, so a quiet stretch renders as a low line rather than as a
 * gap in the chart.
 *
 * One load drives the whole page: the five reports share the same window and
 * are independent of each other, so they are fetched together and any single
 * failure fails the page rather than half of it.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'

import {
  DEFAULT_REPORT_DAYS,
  REPORT_WINDOWS,
  csvToBlob,
  exportReport,
  fetchAlertRanking,
  fetchAlertTrend,
  fetchHostStatus,
  fetchReportAvailability,
  fetchReportSummary,
} from '@/api/ops/reports'
import LineChart from '@/components/charts/LineChart.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncDataWatch } from '@/composables/use-async-data'
import type { ExportableReport } from '@/types/ops'
import { STATUS_LABEL } from '@/types/enums'
import { formatCount, formatDateTime, formatDuration, formatPercent } from '@/utils/format'

/** Number of ranking rows; keeps the report readable on one screen. */
const RANKING_LIMIT = 10

const days = ref(DEFAULT_REPORT_DAYS)
const exportTarget = ref<ExportableReport>('summary')
const exporting = ref(false)

const exportOptions: readonly { value: ExportableReport; label: string }[] = [
  { value: 'summary', label: '总览指标' },
  { value: 'alert-trend', label: '告警趋势' },
  { value: 'alert-ranking', label: '告警排行' },
  { value: 'availability', label: '可用性明细' },
  { value: 'host-status', label: '主机状态分布' },
]

async function loadReports(windowDays: number) {
  const [summary, trend, ranking, availability, hostStatus] = await Promise.all([
    fetchReportSummary(windowDays),
    fetchAlertTrend(windowDays),
    fetchAlertRanking(windowDays, RANKING_LIMIT),
    fetchReportAvailability(windowDays),
    fetchHostStatus(windowDays),
  ])
  return { summary, trend, ranking, availability, hostStatus }
}

const reports = useAsyncDataWatch(() => loadReports(days.value), () => days.value)

const summary = computed(() => reports.data.value?.summary ?? null)
const trend = computed(() => reports.data.value?.trend ?? null)
const ranking = computed(() => reports.data.value?.ranking ?? null)
const availability = computed(() => reports.data.value?.availability ?? null)
const hostStatus = computed(() => reports.data.value?.hostStatus ?? null)

const firedPoints = computed(() =>
  (trend.value?.points ?? []).map((point) => ({ label: point.date.slice(5), value: point.fired })),
)

const resolvedPoints = computed(() =>
  (trend.value?.points ?? []).map((point) => ({
    label: point.date.slice(5),
    value: point.resolved,
  })),
)

/** True only when the installation reported nothing at all. */
const isEmpty = computed(() => {
  const data = summary.value
  if (data === null) {
    return false
  }
  return (
    data.host.total === 0 &&
    data.service.total === 0 &&
    data.alert.fired === 0 &&
    data.availability.check_count === 0 &&
    data.agent.total === 0
  )
})

/**
 * Translate a resource type of an alert ranking row.
 *
 * The row arrives as `DefaultRow` from the table slot, so the field is read
 * through a narrowed shape instead of a declared parameter type.
 */
function resourceLabel(row: unknown): string {
  const value = (row as { resource_type?: string } | null)?.resource_type ?? ''
  return STATUS_LABEL[value] ?? value
}

async function download(): Promise<void> {
  exporting.value = true
  try {
    const document = await exportReport(exportTarget.value, days.value, RANKING_LIMIT)
    const url = URL.createObjectURL(csvToBlob(document.content, document.content_type))
    const anchor = window.document.createElement('a')
    anchor.href = url
    anchor.download = document.filename
    anchor.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${document.filename}`)
  } catch (failure: unknown) {
    ElMessage.error(failure instanceof Error ? failure.message : '导出失败')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader
      title="运维报表"
      description="按时间窗口汇总主机、服务、告警、可用性与通知的整体表现"
    >
      <template #actions>
        <ElSelect v-model="days" class="reports__select">
          <ElOption
            v-for="window in REPORT_WINDOWS"
            :key="window"
            :value="window"
            :label="window === 1 ? '近 1 天' : `近 ${window} 天`"
          />
        </ElSelect>
        <ElSelect v-model="exportTarget" class="reports__select">
          <ElOption
            v-for="option in exportOptions"
            :key="option.value"
            :value="option.value"
            :label="option.label"
          />
        </ElSelect>
        <ElButton :loading="exporting" @click="download()">导出 CSV</ElButton>
        <ElButton @click="reports.reload()">刷新</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="reports.loading.value"
      :failed="reports.failed.value"
      :empty="isEmpty"
      :error="reports.error.value"
      :skeleton-rows="6"
      empty-text="该窗口内还没有任何监控数据"
      @retry="reports.reload()"
    >
      <p class="reports__window">
        窗口：{{ summary?.window.days ?? days }} 天 · 生成于
        {{ formatDateTime(summary?.generated_at) }}
      </p>

      <div class="reports__stats">
        <StatCard
          label="主机在线"
          :value="`${summary?.host.online ?? 0} / ${summary?.host.total ?? 0}`"
          :hint="`在线率 ${formatPercent(summary?.host.online_rate ?? 0)}`"
        />
        <StatCard
          label="异常服务"
          :value="`${summary?.service.abnormal ?? 0} / ${summary?.service.total ?? 0}`"
          hint="降级或宕机"
        />
        <StatCard
          label="告警触发"
          :value="formatCount(summary?.alert.fired ?? 0)"
          :hint="`窗口内新增 ${formatCount(summary?.alert.fired ?? 0)} 条`"
        />
        <StatCard
          label="当前活跃告警"
          :value="formatCount(summary?.alert.active ?? 0)"
          hint="待认领或告警中"
        />
        <StatCard
          label="告警恢复率"
          :value="formatPercent(summary?.alert.resolve_rate ?? 0)"
          :hint="`窗口内恢复 ${formatCount(summary?.alert.resolved ?? 0)} 条`"
        />
        <StatCard
          label="平均恢复时长"
          :value="formatDuration(summary?.alert.mttr_seconds)"
          hint="MTTR"
        />
        <StatCard
          label="可用性成功率"
          :value="formatPercent(summary?.availability.success_rate ?? 0)"
          :hint="`${formatCount(summary?.availability.check_count ?? 0)} 次探测`"
        />
        <StatCard
          label="在线 Agent"
          :value="`${summary?.agent.online ?? 0} / ${summary?.agent.total ?? 0}`"
          hint="采集端心跳"
        />
      </div>

      <div class="reports__charts">
        <section class="vctn-panel">
          <h3 class="vctn-section-title">告警触发趋势</h3>
          <LineChart
            :points="firedPoints"
            series-name="每日告警触发数"
            color="var(--vctn-brand)"
          />
        </section>
        <section class="vctn-panel">
          <h3 class="vctn-section-title">告警恢复趋势</h3>
          <LineChart
            :points="resolvedPoints"
            series-name="每日告警恢复数"
            color="var(--vctn-success)"
          />
        </section>
      </div>

      <section class="vctn-panel vctn-panel--flush">
        <div class="reports__section-header">
          <h3 class="vctn-section-title">告警排行（Top {{ RANKING_LIMIT }}）</h3>
        </div>
        <ElTable :data="ranking?.rows ?? []" class="reports__table">
          <ElTableColumn prop="rank" label="#" width="60" />
          <ElTableColumn label="资源类型" width="110">
            <template #default="{ row }">{{ resourceLabel(row) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="resource_id" label="资源 ID" width="180" />
          <ElTableColumn prop="alert_type" label="告警类型" min-width="140" />
          <ElTableColumn label="最严重" width="110">
            <template #default="{ row }">
              <StatusTag :value="row.worst_severity ?? 'UNKNOWN'" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="total" label="窗口内触发" width="120" />
          <ElTableColumn prop="active" label="当前活跃" width="110" />
          <ElTableColumn label="最后触发" width="180">
            <template #default="{ row }">{{ formatDateTime(row.last_triggered_at) }}</template>
          </ElTableColumn>
          <template #empty>
            <span class="vctn-muted">窗口内没有告警</span>
          </template>
        </ElTable>
      </section>

      <section class="vctn-panel vctn-panel--flush">
        <div class="reports__section-header">
          <h3 class="vctn-section-title">可用性明细</h3>
        </div>
        <ElTable :data="availability?.rows ?? []" class="reports__table">
          <ElTableColumn prop="check_code" label="编码" width="160" />
          <ElTableColumn prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <ElTableColumn prop="target" label="目标" min-width="180" show-overflow-tooltip />
          <ElTableColumn prop="total" label="探测次数" width="110" />
          <ElTableColumn prop="failed" label="失败次数" width="110" />
          <ElTableColumn label="成功率" width="110">
            <template #default="{ row }">{{ formatPercent(row.success_rate) }}</template>
          </ElTableColumn>
          <ElTableColumn label="平均耗时" width="110">
            <template #default="{ row }">{{ row.avg_latency_ms.toFixed(1) }} ms</template>
          </ElTableColumn>
          <ElTableColumn label="最大耗时" width="110">
            <template #default="{ row }">{{ row.max_latency_ms.toFixed(1) }} ms</template>
          </ElTableColumn>
          <template #empty>
            <span class="vctn-muted">窗口内没有探测数据</span>
          </template>
        </ElTable>
      </section>

      <section class="vctn-panel">
        <h3 class="vctn-section-title">主机状态分布</h3>
        <ul v-if="(hostStatus?.rows.length ?? 0) > 0" class="reports__bars">
          <li v-for="row in hostStatus?.rows ?? []" :key="row.status" class="reports__bar">
            <span class="reports__bar-label">
              <StatusTag :value="row.status" />
            </span>
            <span class="reports__bar-track">
              <span
                class="reports__bar-fill"
                :style="{ width: `${Math.max(row.share * 100, 1)}%` }"
              />
            </span>
            <span class="reports__bar-value">
              {{ row.count }}（{{ formatPercent(row.share) }}）
            </span>
          </li>
        </ul>
        <p v-else class="vctn-muted">尚未登记主机</p>
      </section>
    </DataStateView>
  </div>
</template>

<style scoped>
.reports__select {
  width: 130px;
}

.reports__window {
  margin: 0 0 var(--vctn-space-4);
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.reports__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--vctn-space-4);
}

.reports__charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--vctn-space-4);
  margin-top: var(--vctn-space-4);
}

.reports__section-header {
  padding: var(--vctn-space-4) var(--vctn-space-4) 0;
}

.reports__table {
  width: 100%;
}

.reports__bars {
  display: flex;
  flex-direction: column;
  gap: var(--vctn-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.reports__bar {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-3);
}

.reports__bar-label {
  width: 96px;
}

.reports__bar-track {
  flex: 1;
  height: 8px;
  overflow: hidden;
  border-radius: var(--vctn-radius-pill);
  background-color: var(--vctn-bg-subtle);
}

.reports__bar-fill {
  display: block;
  height: 100%;
  border-radius: var(--vctn-radius-pill);
  background-color: var(--vctn-brand);
}

.reports__bar-value {
  min-width: 120px;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-xs);
  font-variant-numeric: tabular-nums;
  text-align: right;
}
</style>
