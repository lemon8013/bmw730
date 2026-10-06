<script setup lang="ts">
/**
 * 工具统计：每个工具的使用次数、按日趋势与热门排行。
 *
 * 管理端以 Operator（sys_user）身份调用，平台侧 `/tools/usage/*` 与
 * `/tools/statistics/*` 读接口要求业务用户身份，Operator 调用会返回 401，
 * 因此本页只使用管理端聚合接口 `/admin/tools/usage*` 与公开的热门榜。
 */
import { computed, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
} from 'element-plus'

import { listPopularTools } from '@/api/catalog'
import {
  getToolUsageDaily,
  getToolUsageOverview,
  getToolUsageTrend,
  listAdminTools,
  listToolUsage,
} from '@/api/tools'
import { refreshStatistics } from '@/api/toolUsage'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type {
  RefreshRequest,
  ToolUsageAdmin,
  ToolUsageOverviewAdmin,
  ToolUsageTrendPointAdmin,
} from '@/types/tools'
import { renderError } from '@/utils/error'
import { formatDateTime, formatNumber, toDateString } from '@/utils/format'

const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolStatView)

/** 热度统计窗口与热门榜单长度。 */
const WINDOW_DAYS = 30
const POPULAR_LIMIT = 10
/** 可选的统计窗口（天）。 */
const USAGE_DAY_OPTIONS = [7, 30, 90]

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

// ---------------------------------------------------------------------------
// 每工具使用次数
// ---------------------------------------------------------------------------

const usageDays = ref(WINDOW_DAYS)

const {
  data: usageRows,
  loading: usageLoading,
  failed: usageFailed,
  error: usageError,
  reload: reloadUsage,
} = useAsyncData(() => listToolUsage(usageDays.value))

const usageTableRows = computed(() => asRows(usageRows.value ?? []))

// ---------------------------------------------------------------------------
// 区间汇总与全站趋势（管理端聚合，跨工具去重）
// ---------------------------------------------------------------------------

const {
  data: overview,
  loading: overviewLoading,
  failed: overviewFailed,
  error: overviewError,
  reload: reloadOverview,
} = useAsyncData<ToolUsageOverviewAdmin | null>(() => getToolUsageOverview(usageDays.value), {
  initial: null,
})

const {
  data: trend,
  loading: trendLoading,
  failed: trendFailed,
  error: trendError,
  reload: reloadTrend,
} = useAsyncData<ToolUsageTrendPointAdmin[]>(() => getToolUsageTrend(usageDays.value), {
  initial: [],
})

/** 趋势图用 `MM-DD` 作为横轴标签，避免日期过长挤压绘图区。 */
function shortDate(value: string): string {
  return value.length >= 10 ? value.slice(5) : value
}

const trendPoints = computed(() =>
  (trend.value ?? []).map((point) => ({
    label: shortDate(point.stat_date),
    value: point.total_count,
  })),
)

const failurePoints = computed(() =>
  (trend.value ?? []).map((point) => ({
    label: shortDate(point.stat_date),
    value: point.failure_count,
  })),
)

/** 调用排行取前 10 名；次要值显示成功次数，便于一眼看出健康度。 */
const RANK_LIMIT = 10

const rankBars = computed(() =>
  (usageRows.value ?? [])
    .slice(0, RANK_LIMIT)
    .map((row) => ({
      label: row.tool_name ?? row.tool_slug ?? row.tool_id,
      value: row.total_count,
      secondary: row.success_count,
    })),
)

/** 成功 / 失败构成，用于占比对比。 */
const outcomeBars = computed(() => {
  const current = overview.value
  if (current === null) {
    return []
  }
  return [
    { label: '成功', value: current.success_count },
    { label: '失败', value: current.failure_count },
  ]
})

function onUsageDaysChange(): void {
  void reloadUsage()
  void reloadOverview()
  void reloadTrend()
  if (selectedToolId.value !== '') {
    void reloadDaily()
  }
}

// ---------------------------------------------------------------------------
// 工具选择与按日趋势
// ---------------------------------------------------------------------------

const statDate = toDateString(new Date())
const selectedToolId = ref('')

const {
  data: toolsPage,
  loading: toolsLoading,
  failed: toolsFailed,
  error: toolsError,
  reload: reloadTools,
} = useAsyncData(() => listAdminTools({ page: 1, page_size: 100 }))

const tools = computed(() => toolsPage.value?.items ?? [])

const {
  data: daily,
  loading: dailyLoading,
  failed: dailyFailed,
  error: dailyError,
  reload: reloadDaily,
} = useAsyncData<ToolUsageAdmin[] | unknown[]>(
  () =>
    selectedToolId.value === ''
      ? Promise.resolve([])
      : getToolUsageDaily(selectedToolId.value, usageDays.value),
  { immediate: false, initial: [] },
)

const bars = computed(() =>
  (daily.value as { stat_date: string; total_count: number }[]).map((item) => ({
    label: item.stat_date,
    value: item.total_count,
  })),
)

function loadTool(): void {
  if (selectedToolId.value === '') {
    notify.warning('请先选择工具')
    return
  }
  void reloadDaily()
}

// ---------------------------------------------------------------------------
// 热门工具
// ---------------------------------------------------------------------------

const {
  data: popular,
  loading: popularLoading,
  failed: popularFailed,
  error: popularError,
  reload: reloadPopular,
} = useAsyncData(() => listPopularTools(WINDOW_DAYS, POPULAR_LIMIT))

const popularRows = computed(() => asRows(popular.value ?? []))

// ---------------------------------------------------------------------------
// 动作
// ---------------------------------------------------------------------------

const refreshing = ref(false)

async function onRefreshStatistics(): Promise<void> {
  refreshing.value = true
  try {
    const payload: RefreshRequest = { stat_date: statDate, window_days: WINDOW_DAYS }
    const result = await refreshStatistics(payload)
    notify.success(`统计已刷新 ${result.refreshed} 条`)
    void reloadPopular()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    refreshing.value = false
  }
}

function reloadAll(): void {
  void reloadTools()
  void reloadUsage()
  void reloadOverview()
  void reloadTrend()
  void reloadPopular()
  if (selectedToolId.value !== '') {
    void reloadDaily()
  }
}
</script>

<template>
  <div class="tool-statistics-page">
    <PageHeader title="工具统计" description="按工具查看调用次数、按日趋势与热门排行。">
      <template #actions>
        <ElButton @click="reloadAll">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.toolStatView"
          type="primary"
          :loading="refreshing"
          @click="onRefreshStatistics"
        >
          刷新统计
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="tool-statistics-page__filters">
      <ElSpace wrap>
        <span class="tool-statistics-page__label">统计区间</span>
        <ElSelect
          v-model="usageDays"
          style="width: 140px"
          @change="onUsageDaysChange"
        >
          <ElOption
            v-for="item in USAGE_DAY_OPTIONS"
            :key="item"
            :label="`近 ${item} 天`"
            :value="item"
          />
        </ElSelect>
        <ElSelect
          v-model="selectedToolId"
          :loading="toolsLoading"
          placeholder="选择工具查看按日趋势"
          filterable
          clearable
          style="width: 320px"
          @change="loadTool"
        >
          <ElOption
            v-for="item in tools"
            :key="item.id"
            :label="`${item.name}（${item.code}）`"
            :value="String(item.id)"
          />
        </ElSelect>
      </ElSpace>
      <ElAlert
        v-if="toolsFailed"
        type="error"
        :closable="false"
        show-icon
        class="tool-statistics-page__alert"
        title="工具列表加载失败"
        :description="toolsError?.message ?? '请稍后重试'"
      />
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">近 {{ usageDays }} 天合计</h4>
      <DataStateView
        :loading="overviewLoading"
        :failed="overviewFailed"
        :error="overviewError"
        :empty="false"
        @retry="reloadOverview"
      >
        <div class="tool-statistics-page__stats">
          <StatCard
            label="总调用次数"
            :value="formatNumber(overview?.total_count ?? 0)"
            :hint="
              overview === null
                ? undefined
                : `${overview.start_date} ~ ${overview.end_date}`
            "
          />
          <StatCard
            label="成功率"
            :value="`${overview?.success_rate ?? 0}%`"
            :hint="
              overview === null
                ? undefined
                : `成功 ${formatNumber(overview.success_count)} / 失败 ${formatNumber(overview.failure_count)}`
            "
          />
          <StatCard
            label="独立用户"
            :value="formatNumber(overview?.unique_user_count ?? 0)"
            hint="区间内去重的登录用户"
          />
          <StatCard
            label="独立访客"
            :value="formatNumber(overview?.unique_guest_count ?? 0)"
            hint="区间内去重的匿名访客"
          />
          <StatCard
            label="活跃工具"
            :value="formatNumber(overview?.active_tool_count ?? 0)"
            hint="区间内被调用过的工具数"
          />
          <StatCard
            label="最近调用"
            :value="overview?.last_used_at ? formatDateTime(overview.last_used_at) : '—'"
          />
        </div>
      </DataStateView>
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">调用趋势（近 {{ usageDays }} 天）</h4>
      <DataStateView
        :loading="trendLoading"
        :failed="trendFailed"
        :error="trendError"
        :empty="trendPoints.length === 0"
        empty-text="所选区间内暂无调用记录"
        @retry="reloadTrend"
      >
        <div class="tool-statistics-page__charts">
          <div>
            <p class="tool-statistics-page__chart-label">每日调用量</p>
            <LineChart :points="trendPoints" series-name="每日调用量" />
          </div>
          <div>
            <p class="tool-statistics-page__chart-label">每日失败数</p>
            <LineChart
              :points="failurePoints"
              series-name="每日失败数"
              color="var(--vctn-danger)"
            />
          </div>
        </div>
      </DataStateView>
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">调用构成与排行</h4>
      <div class="tool-statistics-page__charts">
        <div>
          <p class="tool-statistics-page__chart-label">成功 / 失败</p>
          <BarChart :bars="outcomeBars" empty-text="所选区间内暂无调用记录" />
        </div>
        <div>
          <p class="tool-statistics-page__chart-label">
            工具调用排行（Top {{ RANK_LIMIT }}，数值为调用 / 成功）
          </p>
          <BarChart :bars="rankBars" empty-text="所选区间内暂无调用记录" />
        </div>
      </div>
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">每个工具的使用次数</h4>
      <BaseTable
        :rows="usageTableRows"
        :loading="usageLoading"
        :failed="usageFailed"
        :error="usageError"
        :total="usageTableRows.length"
        :page="1"
        :page-size="usageTableRows.length || 1"
        :paginated="false"
        row-key="tool_id"
        empty-text="所选区间内暂无调用记录"
        @retry="reloadUsage"
      >
        <ElTableColumn v-if="!fields.isHidden('tool_name')" label="工具" min-width="200">
          <template #default="{ row }">
            {{ row.tool_name ?? row.tool_slug ?? row.tool_id }}
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('total_count')" label="使用次数" width="120">
          <template #default="{ row }">{{ formatNumber(row.total_count) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('success_count')" label="成功" width="110">
          <template #default="{ row }">{{ formatNumber(row.success_count) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('failure_count')" label="失败" width="110">
          <template #default="{ row }">{{ formatNumber(row.failure_count) }}</template>
        </ElTableColumn>
        <ElTableColumn label="独立用户" width="120">
          <template #default="{ row }">{{ formatNumber(row.unique_user_count) }}</template>
        </ElTableColumn>
        <ElTableColumn label="独立访客" width="120">
          <template #default="{ row }">{{ formatNumber(row.unique_guest_count) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('last_used_at')" label="最近使用" width="180">
          <template #default="{ row }">
            {{ row.last_used_at ? formatDateTime(row.last_used_at) : '—' }}
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">按日调用趋势</h4>
      <DataStateView
        :loading="dailyLoading"
        :failed="dailyFailed"
        :error="dailyError"
        :empty="bars.length === 0"
        empty-text="请选择工具查看按日趋势"
        @retry="loadTool"
      >
        <BarChart :bars="bars" empty-text="所选区间暂无调用记录" />
      </DataStateView>
    </ElCard>

    <ElCard shadow="never" class="tool-statistics-page__section">
      <h4 class="tool-statistics-page__section-title">热门工具（近 {{ WINDOW_DAYS }} 天）</h4>
      <BaseTable
        :rows="popularRows"
        :loading="popularLoading"
        :failed="popularFailed"
        :error="popularError"
        :total="popularRows.length"
        :page="1"
        :page-size="popularRows.length || 1"
        :paginated="false"
        row-key="tool_id"
        empty-text="暂无热门工具数据"
        @retry="reloadPopular"
      >
        <ElTableColumn label="排名" width="80">
          <template #default="{ row }">{{ row.rank_no ?? '—' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('tool_name')" label="工具" min-width="180">
          <template #default="{ row }">
            {{ row.tool_name ?? row.tool_slug ?? row.tool_id ?? '—' }}
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('usage_count')" label="调用次数" width="120">
          <template #default="{ row }">{{ formatNumber(row.usage_count) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('unique_user_count')"
          label="独立用户"
          width="120"
        >
          <template #default="{ row }">{{ formatNumber(row.unique_user_count) }}</template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>
  </div>
</template>

<style scoped>
.tool-statistics-page__filters {
  margin-bottom: 16px;
}

.tool-statistics-page__label {
  color: var(--vctn-text-regular);
  font-size: 13px;
}

.tool-statistics-page__alert {
  margin-top: 12px;
}

.tool-statistics-page__section {
  margin-bottom: 16px;
}

.tool-statistics-page__section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 500;
}

.tool-statistics-page__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.tool-statistics-page__charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.tool-statistics-page__chart-label {
  margin: 0 0 8px;
  color: var(--vctn-text-secondary);
  font-size: 12px;
}
</style>
