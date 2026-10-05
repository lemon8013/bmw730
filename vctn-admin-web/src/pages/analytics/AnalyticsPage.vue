<script setup lang="ts">
/**
 * 行为分析控制台：总览、事件、用户、页面、工具、搜索、漏斗与留存。
 *
 * 所有数据都来自 `@/api/analytics`。后端未实现留存端点，留存页仅给出说明并复用趋势图。
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCol,
  ElDatePicker,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElRow,
  ElSpace,
  ElSwitch,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  type FormRules,
} from 'element-plus'

import {
  adminRecompute,
  createFunnel,
  deleteFunnel,
  getAdminEventsDaily,
  getAdminOverview,
  getFunnelSummary,
  getPagesDaily,
  getSearchesDaily,
  getToolRankings,
  getToolsDaily,
  getTrends,
  getUsersDaily,
  listFunnels,
  queryEvents,
  updateFunnel,
} from '@/api/analytics'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type {
  BehaviorEvent,
  Funnel,
  FunnelCreateRequest,
  FunnelUpdateRequest,
} from '@/types/analytics'
import { renderError } from '@/utils/error'
import { formatDateTime, formatDuration, formatNumber, lastDaysRange } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.analyticsView)

/** 工具排行榜长度。 */
const RANKING_LIMIT = 10

/** 是否具备导出 / 重算权限。 */
const canExport = computed(() => permission.has(PERMISSION.analyticsExport))

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
// 标签页与日期区间
// ---------------------------------------------------------------------------

const activeTab = ref('overview')

const initialRange = lastDaysRange(30)
const dateRange = ref<[string, string] | null>([initialRange.start, initialRange.end])
const start = computed(() => dateRange.value?.[0] ?? initialRange.start)
const end = computed(() => dateRange.value?.[1] ?? initialRange.end)

const eventCode = ref('')

// ---------------------------------------------------------------------------
// 总览
// ---------------------------------------------------------------------------

const {
  data: overview,
  loading: overviewLoading,
  failed: overviewFailed,
  error: overviewError,
  reload: reloadOverview,
} = useAsyncData(() => getAdminOverview(start.value, end.value))

const {
  data: trends,
  loading: trendsLoading,
  failed: trendsFailed,
  error: trendsError,
  reload: reloadTrends,
} = useAsyncData(() => getTrends(start.value, end.value))

const {
  data: rankings,
  loading: rankingsLoading,
  failed: rankingsFailed,
  error: rankingsError,
  reload: reloadRankings,
} = useAsyncData(() => getToolRankings(start.value, end.value, RANKING_LIMIT))

const pvPoints = computed(() =>
  (trends.value?.points ?? []).map((point) => ({ label: point.stat_date, value: point.pv })),
)

const uvPoints = computed(() =>
  (trends.value?.points ?? []).map((point) => ({ label: point.stat_date, value: point.uv })),
)

const rankingBars = computed(() =>
  (rankings.value ?? []).map((item) => ({
    label: item.tool_id ?? '未知工具',
    value: item.execute_count,
    secondary: item.unique_user_count,
  })),
)

const recomputing = ref(false)

async function onRecompute(): Promise<void> {
  const confirmed = await notify.confirm({
    title: '重算统计数据',
    message: `确定要重算 ${start.value} ~ ${end.value} 的统计数据吗？`,
  })
  if (!confirmed) {
    return
  }
  recomputing.value = true
  try {
    const result = await adminRecompute(start.value, end.value)
    notify.success(`已重算 ${result.recomputed_rows} 行`)
    applyRange()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    recomputing.value = false
  }
}

// ---------------------------------------------------------------------------
// 事件
// ---------------------------------------------------------------------------

const eventsPager = usePagination()
const rawEventsPager = usePagination()

const {
  data: eventsDaily,
  loading: eventsDailyLoading,
  failed: eventsDailyFailed,
  error: eventsDailyError,
  reload: reloadEventsDaily,
} = useAsyncData(() =>
  getAdminEventsDaily({
    event_code: eventCode.value.trim() === '' ? undefined : eventCode.value.trim(),
    start: start.value,
    end: end.value,
    page: eventsPager.page.value,
    page_size: eventsPager.pageSize.value,
  }),
)

watch(eventsDaily, (value) => {
  if (value) {
    eventsPager.applyPage(value)
  }
})

const {
  data: rawEvents,
  loading: rawEventsLoading,
  failed: rawEventsFailed,
  error: rawEventsError,
  reload: reloadRawEvents,
} = useAsyncData(() =>
  queryEvents({
    event_code: eventCode.value.trim() === '' ? undefined : eventCode.value.trim(),
    date_from: start.value,
    date_to: end.value,
    page: rawEventsPager.page.value,
    page_size: rawEventsPager.pageSize.value,
  }),
)

watch(rawEvents, (value) => {
  if (value) {
    rawEventsPager.applyPage(value)
  }
})

const eventDailyRows = computed(() => asRows(eventsDaily.value?.items ?? []))
const rawEventRows = computed(() => asRows(rawEvents.value?.items ?? []))

function onEventSearch(): void {
  eventsPager.changePage(1)
  rawEventsPager.changePage(1)
  void reloadEventsDaily()
  void reloadRawEvents()
}

function onEventsPageChange(next: number): void {
  eventsPager.changePage(next)
  void reloadEventsDaily()
}

function onEventsPageSizeChange(next: number): void {
  eventsPager.changePageSize(next)
  void reloadEventsDaily()
}

function onRawEventsPageChange(next: number): void {
  rawEventsPager.changePage(next)
  void reloadRawEvents()
}

function onRawEventsPageSizeChange(next: number): void {
  rawEventsPager.changePageSize(next)
  void reloadRawEvents()
}

// ---------------------------------------------------------------------------
// 用户 / 页面 / 工具 / 搜索
// ---------------------------------------------------------------------------

const usersPager = usePagination()
const pagesPager = usePagination()
const toolsPager = usePagination()
const searchesPager = usePagination()

const {
  data: usersDaily,
  loading: usersDailyLoading,
  failed: usersDailyFailed,
  error: usersDailyError,
  reload: reloadUsersDaily,
} = useAsyncData(() =>
  getUsersDaily({
    start_date: start.value,
    end_date: end.value,
    page: usersPager.page.value,
    page_size: usersPager.pageSize.value,
  }),
)

watch(usersDaily, (value) => {
  if (value) {
    usersPager.applyPage(value)
  }
})

const {
  data: pagesDaily,
  loading: pagesDailyLoading,
  failed: pagesDailyFailed,
  error: pagesDailyError,
  reload: reloadPagesDaily,
} = useAsyncData(() =>
  getPagesDaily({
    start_date: start.value,
    end_date: end.value,
    page: pagesPager.page.value,
    page_size: pagesPager.pageSize.value,
  }),
)

watch(pagesDaily, (value) => {
  if (value) {
    pagesPager.applyPage(value)
  }
})

const {
  data: toolsDaily,
  loading: toolsDailyLoading,
  failed: toolsDailyFailed,
  error: toolsDailyError,
  reload: reloadToolsDaily,
} = useAsyncData(() =>
  getToolsDaily({
    start_date: start.value,
    end_date: end.value,
    page: toolsPager.page.value,
    page_size: toolsPager.pageSize.value,
  }),
)

watch(toolsDaily, (value) => {
  if (value) {
    toolsPager.applyPage(value)
  }
})

const {
  data: searchesDaily,
  loading: searchesDailyLoading,
  failed: searchesDailyFailed,
  error: searchesDailyError,
  reload: reloadSearchesDaily,
} = useAsyncData(() =>
  getSearchesDaily({
    start_date: start.value,
    end_date: end.value,
    page: searchesPager.page.value,
    page_size: searchesPager.pageSize.value,
  }),
)

watch(searchesDaily, (value) => {
  if (value) {
    searchesPager.applyPage(value)
  }
})

const userDailyRows = computed(() => asRows(usersDaily.value?.items ?? []))
const pageDailyRows = computed(() => asRows(pagesDaily.value?.items ?? []))
const toolDailyRows = computed(() => asRows(toolsDaily.value?.items ?? []))
const searchDailyRows = computed(() => asRows(searchesDaily.value?.items ?? []))

function onUsersPageChange(next: number): void {
  usersPager.changePage(next)
  void reloadUsersDaily()
}
function onUsersPageSizeChange(next: number): void {
  usersPager.changePageSize(next)
  void reloadUsersDaily()
}
function onPagesPageChange(next: number): void {
  pagesPager.changePage(next)
  void reloadPagesDaily()
}
function onPagesPageSizeChange(next: number): void {
  pagesPager.changePageSize(next)
  void reloadPagesDaily()
}
function onToolsPageChange(next: number): void {
  toolsPager.changePage(next)
  void reloadToolsDaily()
}
function onToolsPageSizeChange(next: number): void {
  toolsPager.changePageSize(next)
  void reloadToolsDaily()
}
function onSearchesPageChange(next: number): void {
  searchesPager.changePage(next)
  void reloadSearchesDaily()
}
function onSearchesPageSizeChange(next: number): void {
  searchesPager.changePageSize(next)
  void reloadSearchesDaily()
}

// ---------------------------------------------------------------------------
// 漏斗
// ---------------------------------------------------------------------------

const {
  data: funnelSummary,
  loading: funnelSummaryLoading,
  failed: funnelSummaryFailed,
  error: funnelSummaryError,
  reload: reloadFunnelSummary,
} = useAsyncData(() => getFunnelSummary(start.value, end.value))

const funnelSummaryRows = computed(() => asRows(funnelSummary.value ?? []))

const {
  data: funnels,
  loading: funnelsLoading,
  failed: funnelsFailed,
  error: funnelsError,
  reload: reloadFunnels,
} = useAsyncData(() => listFunnels())

const funnelRows = computed(() => asRows(funnels.value ?? []))

interface FunnelFormModel {
  funnel_code: string
  funnel_name: string
  step_no: number
  step_code: string
  event_code: string
  enabled: boolean
}

const funnelForm = reactive<FunnelFormModel>({
  funnel_code: '',
  funnel_name: '',
  step_no: 1,
  step_code: '',
  event_code: '',
  enabled: true,
})

const funnelRules: FormRules = {
  funnel_code: [{ required: true, message: '请输入漏斗编码', trigger: 'blur' }],
  funnel_name: [{ required: true, message: '请输入漏斗名称', trigger: 'blur' }],
  step_code: [{ required: true, message: '请输入步骤编码', trigger: 'blur' }],
  event_code: [{ required: true, message: '请输入事件编码', trigger: 'blur' }],
}

const funnelDialogVisible = ref(false)
const funnelEditingId = ref<string | null>(null)
const funnelSubmitting = ref(false)
const funnelSubmitError = ref<string | null>(null)
const funnelSubmitTrace = ref<string | null>(null)
const funnelFormRef = ref<InstanceType<typeof BaseForm>>()

function clearFunnelError(): void {
  funnelSubmitError.value = null
  funnelSubmitTrace.value = null
}

function openFunnelCreate(): void {
  funnelEditingId.value = null
  funnelForm.funnel_code = ''
  funnelForm.funnel_name = ''
  funnelForm.step_no = 1
  funnelForm.step_code = ''
  funnelForm.event_code = ''
  funnelForm.enabled = true
  clearFunnelError()
  funnelDialogVisible.value = true
}

function openFunnelEdit(row: Record<string, unknown>): void {
  const funnel = row as unknown as Funnel
  funnelEditingId.value = funnel.id
  funnelForm.funnel_code = funnel.funnel_code
  funnelForm.funnel_name = funnel.funnel_name
  funnelForm.step_no = funnel.step_no
  funnelForm.step_code = funnel.step_code
  funnelForm.event_code = funnel.event_code
  funnelForm.enabled = funnel.enabled
  clearFunnelError()
  funnelDialogVisible.value = true
}

async function submitFunnel(): Promise<void> {
  const valid = await funnelFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearFunnelError()
  funnelSubmitting.value = true
  try {
    if (funnelEditingId.value === null) {
      const payload: FunnelCreateRequest = {
        funnel_code: funnelForm.funnel_code,
        funnel_name: funnelForm.funnel_name,
        step_no: funnelForm.step_no,
        step_code: funnelForm.step_code,
        event_code: funnelForm.event_code,
        enabled: funnelForm.enabled,
      }
      await createFunnel(payload)
      notify.success('漏斗步骤已创建')
    } else {
      const payload: FunnelUpdateRequest = {
        funnel_name: funnelForm.funnel_name,
        step_no: funnelForm.step_no,
        step_code: funnelForm.step_code,
        event_code: funnelForm.event_code,
        enabled: funnelForm.enabled,
      }
      await updateFunnel(funnelEditingId.value, payload)
      notify.success('漏斗步骤已更新')
    }
    funnelDialogVisible.value = false
    await reloadFunnels()
    await reloadFunnelSummary()
  } catch (caught) {
    const rendered = renderError(caught)
    funnelSubmitError.value = rendered.message
    funnelSubmitTrace.value = rendered.traceId ?? null
  } finally {
    funnelSubmitting.value = false
  }
}

async function onDeleteFunnel(row: Record<string, unknown>): Promise<void> {
  const funnel = row as unknown as Funnel
  const confirmed = await notify.confirm({
    title: '删除漏斗步骤',
    message: `确定要删除漏斗步骤「${funnel.funnel_code} / ${funnel.step_code}」吗？该操作不可撤销。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteFunnel(funnel.id)
    notify.success('漏斗步骤已删除')
    await reloadFunnels()
    await reloadFunnelSummary()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 统一刷新
// ---------------------------------------------------------------------------

function applyRange(): void {
  eventsPager.changePage(1)
  rawEventsPager.changePage(1)
  usersPager.changePage(1)
  pagesPager.changePage(1)
  toolsPager.changePage(1)
  searchesPager.changePage(1)
  void reloadOverview()
  void reloadTrends()
  void reloadRankings()
  void reloadFunnelSummary()
  void reloadEventsDaily()
  void reloadRawEvents()
  void reloadUsersDaily()
  void reloadPagesDaily()
  void reloadToolsDaily()
  void reloadSearchesDaily()
}

function reloadActive(): void {
  if (activeTab.value === 'overview') {
    void reloadOverview()
    void reloadTrends()
    void reloadRankings()
  } else if (activeTab.value === 'events') {
    void reloadEventsDaily()
    void reloadRawEvents()
  } else if (activeTab.value === 'users') {
    void reloadUsersDaily()
  } else if (activeTab.value === 'pages') {
    void reloadPagesDaily()
  } else if (activeTab.value === 'tools') {
    void reloadToolsDaily()
  } else if (activeTab.value === 'searches') {
    void reloadSearchesDaily()
  } else if (activeTab.value === 'funnel') {
    void reloadFunnelSummary()
    void reloadFunnels()
  } else if (activeTab.value === 'retention') {
    void reloadTrends()
  }
}

/** BehaviorEvent 行在展开时渲染 properties。 */
function rowProperties(row: Record<string, unknown>): unknown {
  const event = row as unknown as BehaviorEvent
  return event.properties ?? null
}
</script>

<template>
  <div class="analytics-page">
    <PageHeader title="行为分析" description="查看平台行为事件的统计、排行与漏斗；数据来自行为分析接口。">
      <template #actions>
        <ElButton @click="reloadActive">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="analytics-page__filters">
      <ElSpace wrap>
        <ElDatePicker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :clearable="false"
          @change="applyRange"
        />
        <span class="analytics-page__range">当前区间：{{ start }} ~ {{ end }}</span>
      </ElSpace>
    </ElCard>

    <ElTabs v-model="activeTab" type="border-card" class="analytics-page__tabs">
      <!-- 总览 -->
      <ElTabPane label="总览" name="overview">
        <DataStateView
          :loading="overviewLoading"
          :failed="overviewFailed"
          :error="overviewError"
          :empty="overview === null"
          empty-text="所选区间暂无总览数据"
          @retry="reloadOverview"
        >
          <template v-if="overview">
            <ElRow :gutter="16" class="analytics-page__stats">
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="事件总量" :value="formatNumber(overview.event_total)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="事件用户数" :value="formatNumber(overview.event_unique_users)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="匿名事件数" :value="formatNumber(overview.event_unique_anonymous)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="页面浏览" :value="formatNumber(overview.page_views)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="工具查看" :value="formatNumber(overview.tool_views)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="工具执行" :value="formatNumber(overview.tool_executions)" />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard
                  label="执行成功 / 失败"
                  :value="`${formatNumber(overview.tool_success)} / ${formatNumber(overview.tool_failure)}`"
                />
              </ElCol>
              <ElCol :xs="24" :sm="12" :md="6">
                <StatCard label="活跃用户天" :value="formatNumber(overview.active_user_days)" />
              </ElCol>
            </ElRow>
            <div class="analytics-page__actions">
              <ElButton
                v-if="canExport"
                v-permission="PERMISSION.analyticsExport"
                type="primary"
                :loading="recomputing"
                @click="onRecompute"
              >
                重算统计
              </ElButton>
            </div>
          </template>
        </DataStateView>

        <ElCard shadow="never" class="analytics-page__card">
          <template #header>趋势（PV）</template>
          <DataStateView
            :loading="trendsLoading"
            :failed="trendsFailed"
            :error="trendsError"
            :empty="pvPoints.length === 0"
            empty-text="所选区间暂无趋势数据"
            @retry="reloadTrends"
          >
            <LineChart :points="pvPoints" series-name="页面浏览趋势 PV" />
          </DataStateView>
        </ElCard>

        <ElCard shadow="never" class="analytics-page__card">
          <template #header>趋势（UV）</template>
          <DataStateView
            :loading="trendsLoading"
            :failed="trendsFailed"
            :error="trendsError"
            :empty="uvPoints.length === 0"
            empty-text="所选区间暂无趋势数据"
            @retry="reloadTrends"
          >
            <LineChart :points="uvPoints" series-name="独立访客趋势 UV" color="#67c23a" />
          </DataStateView>
        </ElCard>

        <ElCard shadow="never" class="analytics-page__card">
          <template #header>工具排行（执行次数）</template>
          <DataStateView
            :loading="rankingsLoading"
            :failed="rankingsFailed"
            :error="rankingsError"
            :empty="rankingBars.length === 0"
            empty-text="所选区间暂无工具排行"
            @retry="reloadRankings"
          >
            <BarChart :bars="rankingBars" empty-text="所选区间暂无工具排行" />
          </DataStateView>
        </ElCard>
      </ElTabPane>

      <!-- 事件 -->
      <ElTabPane label="事件" name="events">
        <ElSpace wrap class="analytics-page__filters-inline">
          <ElInput
            v-model="eventCode"
            placeholder="按事件编码筛选"
            clearable
            style="width: 220px"
            @keyup.enter="onEventSearch"
          />
          <ElButton type="primary" @click="onEventSearch">查询</ElButton>
        </ElSpace>

        <ElCard shadow="never" class="analytics-page__card">
          <template #header>按日事件统计</template>
          <BaseTable
            :rows="eventDailyRows"
            :loading="eventsDailyLoading"
            :failed="eventsDailyFailed"
            :error="eventsDailyError"
            :total="eventsPager.total.value"
            :page="eventsPager.page.value"
            :page-size="eventsPager.pageSize.value"
            empty-text="暂无按日事件统计"
            @retry="reloadEventsDaily"
            @update:page="onEventsPageChange"
            @update:page-size="onEventsPageSizeChange"
          >
            <ElTableColumn label="统计日期" width="140">
              <template #default="{ row }">{{ row.stat_date }}</template>
            </ElTableColumn>
            <ElTableColumn prop="event_code" label="事件编码" min-width="180" />
            <ElTableColumn label="总量" width="110">
              <template #default="{ row }">{{ formatNumber(row.total_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="去重用户" width="120">
              <template #default="{ row }">{{ formatNumber(row.unique_user_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="去重匿名" width="120">
              <template #default="{ row }">{{ formatNumber(row.unique_anonymous_count) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>

        <ElCard shadow="never" class="analytics-page__card">
          <template #header>原始事件</template>
          <BaseTable
            :rows="rawEventRows"
            :loading="rawEventsLoading"
            :failed="rawEventsFailed"
            :error="rawEventsError"
            :total="rawEventsPager.total.value"
            :page="rawEventsPager.page.value"
            :page-size="rawEventsPager.pageSize.value"
            empty-text="暂无原始事件"
            @retry="reloadRawEvents"
            @update:page="onRawEventsPageChange"
            @update:page-size="onRawEventsPageSizeChange"
          >
            <ElTableColumn type="expand">
              <template #default="{ row }">
                <JsonViewer :value="rowProperties(row)" />
              </template>
            </ElTableColumn>
            <ElTableColumn prop="event_code" label="事件编码" min-width="160" />
            <ElTableColumn prop="event_id" label="事件 ID" min-width="200" show-overflow-tooltip />
            <ElTableColumn prop="page_code" label="页面编码" width="140" />
            <ElTableColumn label="发生时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
            </ElTableColumn>
            <ElTableColumn label="接收时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.received_at) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 用户 -->
      <ElTabPane label="用户" name="users">
        <ElCard shadow="never">
          <BaseTable
            :rows="userDailyRows"
            :loading="usersDailyLoading"
            :failed="usersDailyFailed"
            :error="usersDailyError"
            :total="usersPager.total.value"
            :page="usersPager.page.value"
            :page-size="usersPager.pageSize.value"
            empty-text="暂无用户日统计"
            @retry="reloadUsersDaily"
            @update:page="onUsersPageChange"
            @update:page-size="onUsersPageSizeChange"
          >
            <ElTableColumn label="统计日期" width="140">
              <template #default="{ row }">{{ row.stat_date }}</template>
            </ElTableColumn>
            <ElTableColumn prop="user_id" label="用户 ID" min-width="160" />
            <ElTableColumn
              prop="anonymous_id_hash"
              label="匿名标识"
              min-width="180"
              show-overflow-tooltip
            />
            <ElTableColumn label="事件数" width="110">
              <template #default="{ row }">{{ formatNumber(row.event_count) }}</template>
            </ElTableColumn>
            <ElTableColumn prop="active" label="活跃" width="90">
              <template #default="{ row }">
                <StatusTag :value="row.active" :boolean-labels="['不活跃', '活跃']" />
              </template>
            </ElTableColumn>
            <ElTableColumn label="最后事件" width="180">
              <template #default="{ row }">{{ formatDateTime(row.last_event_at) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 页面 -->
      <ElTabPane label="页面" name="pages">
        <ElCard shadow="never">
          <BaseTable
            :rows="pageDailyRows"
            :loading="pagesDailyLoading"
            :failed="pagesDailyFailed"
            :error="pagesDailyError"
            :total="pagesPager.total.value"
            :page="pagesPager.page.value"
            :page-size="pagesPager.pageSize.value"
            empty-text="暂无页面日统计"
            @retry="reloadPagesDaily"
            @update:page="onPagesPageChange"
            @update:page-size="onPagesPageSizeChange"
          >
            <ElTableColumn label="统计日期" width="140">
              <template #default="{ row }">{{ row.stat_date }}</template>
            </ElTableColumn>
            <ElTableColumn prop="page_code" label="页面编码" min-width="180" />
            <ElTableColumn label="浏览量" width="110">
              <template #default="{ row }">{{ formatNumber(row.view_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="去重用户" width="120">
              <template #default="{ row }">{{ formatNumber(row.unique_user_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="去重匿名" width="120">
              <template #default="{ row }">{{ formatNumber(row.unique_anonymous_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="平均时长" width="120">
              <template #default="{ row }">{{ formatDuration(row.avg_duration_ms) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 工具 -->
      <ElTabPane label="工具" name="tools">
        <ElCard shadow="never">
          <BaseTable
            :rows="toolDailyRows"
            :loading="toolsDailyLoading"
            :failed="toolsDailyFailed"
            :error="toolsDailyError"
            :total="toolsPager.total.value"
            :page="toolsPager.page.value"
            :page-size="toolsPager.pageSize.value"
            empty-text="暂无工具日统计"
            @retry="reloadToolsDaily"
            @update:page="onToolsPageChange"
            @update:page-size="onToolsPageSizeChange"
          >
            <ElTableColumn label="统计日期" width="140">
              <template #default="{ row }">{{ row.stat_date }}</template>
            </ElTableColumn>
            <ElTableColumn prop="tool_id" label="工具 ID" min-width="160" />
            <ElTableColumn label="查看" width="90">
              <template #default="{ row }">{{ formatNumber(row.view_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="开始" width="90">
              <template #default="{ row }">{{ formatNumber(row.start_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="执行" width="90">
              <template #default="{ row }">{{ formatNumber(row.execute_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="成功" width="90">
              <template #default="{ row }">{{ formatNumber(row.success_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="失败" width="90">
              <template #default="{ row }">{{ formatNumber(row.failure_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="去重用户" width="110">
              <template #default="{ row }">{{ formatNumber(row.unique_user_count) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 搜索 -->
      <ElTabPane label="搜索" name="searches">
        <ElCard shadow="never">
          <BaseTable
            :rows="searchDailyRows"
            :loading="searchesDailyLoading"
            :failed="searchesDailyFailed"
            :error="searchesDailyError"
            :total="searchesPager.total.value"
            :page="searchesPager.page.value"
            :page-size="searchesPager.pageSize.value"
            empty-text="暂无搜索日统计"
            @retry="reloadSearchesDaily"
            @update:page="onSearchesPageChange"
            @update:page-size="onSearchesPageSizeChange"
          >
            <ElTableColumn label="统计日期" width="140">
              <template #default="{ row }">{{ row.stat_date }}</template>
            </ElTableColumn>
            <ElTableColumn prop="search_type" label="搜索类型" width="150" />
            <ElTableColumn prop="keyword_hash" label="关键词哈希" min-width="220" show-overflow-tooltip />
            <ElTableColumn label="搜索次数" width="120">
              <template #default="{ row }">{{ formatNumber(row.search_count) }}</template>
            </ElTableColumn>
            <ElTableColumn label="结果点击" width="120">
              <template #default="{ row }">{{ formatNumber(row.result_click_count) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 漏斗 -->
      <ElTabPane label="漏斗" name="funnel">
        <ElCard shadow="never" class="analytics-page__card">
          <template #header>漏斗汇总</template>
          <BaseTable
            :rows="funnelSummaryRows"
            :loading="funnelSummaryLoading"
            :failed="funnelSummaryFailed"
            :error="funnelSummaryError"
            :total="funnelSummaryRows.length"
            :page="1"
            :page-size="funnelSummaryRows.length || 1"
            :paginated="false"
            row-key="funnel_code"
            empty-text="所选区间暂无漏斗数据"
            @retry="reloadFunnelSummary"
          >
            <ElTableColumn type="expand">
              <template #default="{ row }">
                <ul class="analytics-page__steps">
                  <li v-for="step in row.steps" :key="`${row.funnel_code}-${step.step_no}`">
                    步骤 {{ step.step_no }} · {{ step.step_code }} · {{ step.event_code }} ·
                    事件数 {{ step.event_count }} ·
                    <StatusTag :value="step.enabled" :boolean-labels="['停用', '启用']" />
                  </li>
                </ul>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="funnel_code" label="漏斗编码" min-width="160" />
            <ElTableColumn prop="funnel_name" label="漏斗名称" min-width="160" />
            <ElTableColumn label="首步人数" width="120">
              <template #default="{ row }">{{ formatNumber(row.first_step_count) }}</template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>

        <ElCard shadow="never">
          <template #header>
            <div class="analytics-page__card-header">
              <span>漏斗定义</span>
              <ElButton type="primary" @click="openFunnelCreate">新建步骤</ElButton>
            </div>
          </template>
          <BaseTable
            :rows="funnelRows"
            :loading="funnelsLoading"
            :failed="funnelsFailed"
            :error="funnelsError"
            :total="funnelRows.length"
            :page="1"
            :page-size="funnelRows.length || 1"
            :paginated="false"
            empty-text="暂无漏斗定义"
            @retry="reloadFunnels"
          >
            <ElTableColumn prop="funnel_code" label="漏斗编码" min-width="150" />
            <ElTableColumn prop="funnel_name" label="漏斗名称" min-width="150" />
            <ElTableColumn prop="step_no" label="步骤序号" width="100" />
            <ElTableColumn prop="step_code" label="步骤编码" min-width="140" />
            <ElTableColumn prop="event_code" label="事件编码" min-width="160" />
            <ElTableColumn prop="enabled" label="启用" width="90">
              <template #default="{ row }">
                <StatusTag :value="row.enabled" :boolean-labels="['禁用', '启用']" />
              </template>
            </ElTableColumn>
            <ElTableColumn label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <ElSpace wrap>
                  <ElButton link type="primary" @click="openFunnelEdit(row)">编辑</ElButton>
                  <ElButton link type="danger" @click="onDeleteFunnel(row)">删除</ElButton>
                </ElSpace>
              </template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElTabPane>

      <!-- 留存 -->
      <ElTabPane label="留存" name="retention">
        <ElAlert
          type="warning"
          :closable="false"
          show-icon
          title="留存接口未实现"
          description="后端尚未提供留存（retention）分析端点，因此本页不生成留存数据，仅复用趋势图作为最接近的可用信号。"
          class="analytics-page__card"
        />
        <ElCard shadow="never" class="analytics-page__card">
          <template #header>趋势（PV）</template>
          <DataStateView
            :loading="trendsLoading"
            :failed="trendsFailed"
            :error="trendsError"
            :empty="pvPoints.length === 0"
            empty-text="所选区间暂无趋势数据"
            @retry="reloadTrends"
          >
            <LineChart :points="pvPoints" series-name="页面浏览趋势 PV" />
          </DataStateView>
        </ElCard>
        <ElCard shadow="never" class="analytics-page__card">
          <template #header>趋势（UV）</template>
          <DataStateView
            :loading="trendsLoading"
            :failed="trendsFailed"
            :error="trendsError"
            :empty="uvPoints.length === 0"
            empty-text="所选区间暂无趋势数据"
            @retry="reloadTrends"
          >
            <LineChart :points="uvPoints" series-name="独立访客趋势 UV" color="#67c23a" />
          </DataStateView>
        </ElCard>
      </ElTabPane>
    </ElTabs>

    <BaseDialog
      v-model="funnelDialogVisible"
      :title="funnelEditingId === null ? '新建漏斗步骤' : '编辑漏斗步骤'"
      :confirm-loading="funnelSubmitting"
      @confirm="submitFunnel"
    >
      <BaseForm
        ref="funnelFormRef"
        :model="funnelForm"
        :rules="funnelRules"
        :error-message="funnelSubmitError"
        :error-trace-id="funnelSubmitTrace"
        hide-footer
      >
        <ElFormItem
          v-if="!fields.isHidden('funnel_code')"
          label="漏斗编码"
          prop="funnel_code"
        >
          <ElInput
            v-model="funnelForm.funnel_code"
            :disabled="funnelEditingId !== null || fields.isReadOnly('funnel_code')"
            placeholder="例如 SIGNUP"
          />
        </ElFormItem>
        <ElFormItem
          v-if="!fields.isHidden('funnel_name')"
          label="漏斗名称"
          prop="funnel_name"
        >
          <ElInput
            v-model="funnelForm.funnel_name"
            :disabled="fields.isReadOnly('funnel_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('step_no')" label="步骤序号">
          <ElInputNumber
            v-model="funnelForm.step_no"
            :min="1"
            :disabled="fields.isReadOnly('step_no')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('step_code')" label="步骤编码" prop="step_code">
          <ElInput v-model="funnelForm.step_code" :disabled="fields.isReadOnly('step_code')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('event_code')" label="事件编码" prop="event_code">
          <ElInput v-model="funnelForm.event_code" :disabled="fields.isReadOnly('event_code')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('enabled')" label="启用">
          <ElSwitch v-model="funnelForm.enabled" :disabled="fields.isReadOnly('enabled')" />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.analytics-page__filters {
  margin-bottom: 16px;
}

.analytics-page__range {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.analytics-page__tabs {
  margin-bottom: 16px;
}

.analytics-page__stats {
  margin-bottom: 16px;
}

.analytics-page__actions {
  margin-bottom: 16px;
}

.analytics-page__card {
  margin-bottom: 16px;
}

.analytics-page__filters-inline {
  margin-bottom: 16px;
}

.analytics-page__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.analytics-page__steps {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
}
</style>
