<script setup lang="ts">
/**
 * Metric definitions and one series at a time.
 *
 * `start`, `end` and `step` are all mandatory on the backend: the window is the
 * caller's decision, so the page always sends one rather than letting the
 * server guess. The chart is inline SVG — the console already ships Element
 * Plus, and a charting library for one trend line is not worth the bundle.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
} from 'element-plus'

import { fetchMetricSeries, listMetrics } from '@/api/ops/metrics'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import LineChart from '@/components/charts/LineChart.vue'
import StatCard from '@/components/charts/StatCard.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import type { MetricDefinition } from '@/types/ops'
import { formatDateTime, formatTime, orEmpty } from '@/utils/format'

const STEP_OPTIONS = ['1m', '5m', '15m', '1h', '6h', '24h'] as const

/** Default window: the last six hours. */
function defaultRange(): [string, string] {
  const end = new Date()
  const start = new Date(end.getTime() - 6 * 60 * 60 * 1000)
  return [start.toISOString(), end.toISOString()]
}

const keyword = ref('')

const list = usePagedList<MetricDefinition>((page, pageSize) =>
  listMetrics(
    page,
    pageSize,
    keyword.value.trim() === '' ? undefined : keyword.value.trim(),
  ),
)

void list.reload()

const metricKey = ref('')
const step = ref<string>('5m')
const range = ref<[string, string]>(defaultRange())

const series = useAsyncData(() =>
  metricKey.value === ''
    ? Promise.resolve(null)
    : fetchMetricSeries({
        metricKey: metricKey.value,
        start: range.value[0],
        end: range.value[1],
        step: step.value,
      }),
)

const points = computed(() =>
  (series.data.value ?? []).map((point) => ({
    label: formatTime(point.timestamp),
    value: point.value,
  })),
)

const latest = computed(() => {
  const values = series.data.value ?? []
  return values.length === 0 ? null : values[values.length - 1]
})

/** Pick a metric from the list without retyping its key. */
function useMetric(row: MetricDefinition): void {
  metricKey.value = row.metric_key
  void series.reload()
}

async function loadSeries(): Promise<void> {
  if (metricKey.value === '') {
    ElMessage.warning('请先选择或输入 metric_key')
    return
  }
  await series.reload()
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="指标中心" description="指标定义清单与时间序列查询" />

    <div class="vctn-panel">
      <h3 class="vctn-section-title">序列查询</h3>
      <div class="metrics__query">
        <ElInput
          v-model="metricKey"
          placeholder="metric_key，例如 host.cpu_usage"
          clearable
          class="metrics__key"
        />
        <ElSelect v-model="step" class="metrics__step">
          <ElOption v-for="option in STEP_OPTIONS" :key="option" :value="option" :label="option" />
        </ElSelect>
        <ElDatePicker
          v-model="range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="metrics__range"
        />
        <ElButton type="primary" @click="loadSeries">查询序列</ElButton>
      </div>

      <p v-if="series.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="series.failed.value" class="vctn-muted">
        {{ series.error.value ?? '序列加载失败' }}
      </p>
      <template v-else-if="series.data.value !== null">
        <div class="metrics__stats">
          <StatCard label="最新值" :value="orEmpty(latest?.value)" />
          <StatCard label="最小值" :value="orEmpty(latest?.min_value)" />
          <StatCard label="最大值" :value="orEmpty(latest?.max_value)" />
          <StatCard label="点数" :value="points.length" />
        </div>
        <LineChart :points="points" :series-name="metricKey" class="metrics__chart" />
      </template>
      <p v-else class="vctn-muted">选择指标与时间范围后查看序列</p>
    </div>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="keyword"
          placeholder="指标键 / 名称"
          clearable
          class="metrics__keyword"
          @keyup.enter="list.search()"
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
      empty-text="没有匹配的指标定义"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="metric_key" label="指标键" min-width="200" show-overflow-tooltip />
      <ElTableColumn prop="metric_name" label="名称" min-width="180" show-overflow-tooltip />
      <ElTableColumn prop="metric_type" label="类型" width="120" />
      <ElTableColumn label="单位" width="100">
        <template #default="{ row }">{{ orEmpty(row.unit) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <ElTableColumn label="更新时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="useMetric(row)">查看序列</ElButton>
      </template>
    </BaseTable>
  </div>
</template>

<style scoped>
.metrics__query {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-2);
  align-items: center;
}

.metrics__key {
  width: 280px;
}

.metrics__step {
  width: 110px;
}

.metrics__range {
  width: 360px;
}

.metrics__keyword {
  width: 240px;
}

.metrics__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--vctn-space-3);
  margin-top: var(--vctn-space-4);
}

.metrics__chart {
  margin-top: var(--vctn-space-4);
}
</style>
