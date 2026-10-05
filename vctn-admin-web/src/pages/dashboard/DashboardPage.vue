<script setup lang="ts">
/**
 * Dashboard.
 *
 * Reads the admin analytics overview, the page-view trend and the runtime
 * version probe, so a fresh deployment can tell at a glance whether the backend
 * is reachable and whether any behaviour has been recorded yet.
 */
import { computed } from 'vue'
import { ElAlert, ElButton, ElCard, ElCol, ElRow, ElTag } from 'element-plus'

import { getAdminOverview, getTrends } from '@/api/analytics'
import { version } from '@/api/health'
import BarChart from '@/components/charts/BarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import { formatNumber, lastDaysRange } from '@/utils/format'

const appStore = useAppStore()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

const window = lastDaysRange(30)

const {
  data: overview,
  loading: overviewLoading,
  failed: overviewFailed,
  error: overviewError,
  reload: reloadOverview,
} = useAsyncData(() => getAdminOverview(window.start, window.end))

const {
  data: trends,
  loading: trendsLoading,
  failed: trendsFailed,
  error: trendsError,
  reload: reloadTrends,
} = useAsyncData(() => getTrends(window.start, window.end))

const { data: backendVersion, reload: reloadBackendVersion } = useAsyncData(() => version())

const eventBars = computed(() => [
  { label: '页面浏览', value: overview.value?.page_views ?? 0 },
  { label: '工具查看', value: overview.value?.tool_views ?? 0 },
  { label: '工具开始', value: overview.value?.tool_starts ?? 0 },
  { label: '工具执行', value: overview.value?.tool_executions ?? 0 },
  { label: '执行成功', value: overview.value?.tool_success ?? 0 },
  { label: '执行失败', value: overview.value?.tool_failure ?? 0 },
])

const trendPoints = computed(() =>
  (trends.value?.points ?? []).map((point) => ({ label: point.stat_date, value: point.pv })),
)

/** Whether the analytics dashboard permission was granted to this identity. */
const canViewAnalytics = computed(() => permissionStore.has('ANALYTICS_DASHBOARD_VIEW'))

const versionLabel = computed(() => backendVersion.value?.version ?? '—')

function refreshAll(): void {
  void reloadOverview()
  void reloadTrends()
  void reloadBackendVersion()
}
</script>

<template>
  <div class="dashboard">
    <PageHeader
      :title="`欢迎，${authStore.displayName || authStore.username}`"
      description="平台概览、运行状态与最近 30 天的行为统计。"
    >
      <template #actions>
        <ElTag type="info" size="small">{{ appStore.apiPrefix }}</ElTag>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      v-if="!canViewAnalytics"
      type="info"
      :closable="false"
      show-icon
      title="未授予数据分析权限"
      description="当前账号没有 ANALYTICS_DASHBOARD_VIEW，统计区域不会返回数据。"
      class="dashboard__notice"
    />

    <ElRow :gutter="16" class="dashboard__stats">
      <ElCol :xs="24" :sm="12" :md="6">
        <StatCard label="后端版本" :value="versionLabel" hint="GET /version" />
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <StatCard label="事件总量" :value="formatNumber(overview?.event_total)" hint="最近 30 天" />
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <StatCard
          label="活跃用户"
          :value="formatNumber(overview?.event_unique_users)"
          hint="去重后的事件用户数"
        />
      </ElCol>
      <ElCol :xs="24" :sm="12" :md="6">
        <StatCard
          label="工具执行"
          :value="formatNumber(overview?.tool_executions)"
          :hint="`成功 ${formatNumber(overview?.tool_success)} / 失败 ${formatNumber(overview?.tool_failure)}`"
        />
      </ElCol>
    </ElRow>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never" class="dashboard__card">
          <template #header>行为事件分布</template>
          <DataStateView
            :loading="overviewLoading"
            :failed="overviewFailed"
            :error="overviewError"
            :empty="overview === null"
            @retry="reloadOverview"
          >
            <BarChart :bars="eventBars" />
          </DataStateView>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="12">
        <ElCard shadow="never" class="dashboard__card">
          <template #header>页面浏览趋势（PV）</template>
          <DataStateView
            :loading="trendsLoading"
            :failed="trendsFailed"
            :error="trendsError"
            :empty="trendPoints.length === 0"
            empty-text="所选区间内没有页面浏览记录"
            @retry="reloadTrends"
          >
            <LineChart :points="trendPoints" series-name="页面浏览趋势" />
          </DataStateView>
        </ElCard>
      </ElCol>
    </ElRow>

    <ElCard shadow="never" class="dashboard__card">
      <template #header>当前会话</template>
      <ul class="dashboard__facts">
        <li>
          账号：{{ authStore.username }}（<StatusTag
            :value="authStore.isSuperAdmin"
            :boolean-labels="['普通管理员', '超级管理员']"
          />）
        </li>
        <li>权限码数量：{{ permissionStore.codes.size }}</li>
        <li>可见菜单分组：{{ permissionStore.menuGroups.length }}</li>
        <li>已接入页面路由：{{ permissionStore.routeRecords.length }}</li>
        <li v-if="permissionStore.unwiredCodes.length">
          未接入的后端菜单项：{{ permissionStore.unwiredCodes.join('、') }}
        </li>
      </ul>
    </ElCard>
  </div>
</template>

<style scoped>
.dashboard__notice {
  margin-bottom: 16px;
}

.dashboard__stats {
  margin-bottom: 16px;
}

.dashboard__card {
  margin-bottom: 16px;
}

.dashboard__facts {
  margin: 0;
  padding-left: 18px;
  line-height: 2;
}
</style>
