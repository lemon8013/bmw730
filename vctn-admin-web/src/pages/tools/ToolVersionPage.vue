<script setup lang="ts">
/** 工具版本：只读查看工具的当前版本与用量汇总。 */
import { computed, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElOption,
  ElSelect,
  ElSpace,
} from 'element-plus'

import { listAdminTools, getAdminTool } from '@/api/tools'
import { getUsageSummary } from '@/api/toolUsage'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import StatCard from '@/components/charts/StatCard.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type { Tool, ToolUsageSummary } from '@/types/tools'
import { TOOL_MODE_LABEL } from '@/types/enums'
import { formatDuration, formatNumber, lastDaysRange } from '@/utils/format'

const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolVersionView)

const initialRange = lastDaysRange(30)
const dateRange = ref<[string, string] | null>([initialRange.start, initialRange.end])
const selectedToolId = ref('')

// ---------------------------------------------------------------------------
// 工具选择
// ---------------------------------------------------------------------------

const { data: toolsPage, loading: toolsLoading, failed: toolsFailed, error: toolsError, reload: reloadTools } =
  useAsyncData(() => listAdminTools({ page: 1, page_size: 100 }))

const tools = computed(() => toolsPage.value?.items ?? [])

// ---------------------------------------------------------------------------
// 版本与用量
// ---------------------------------------------------------------------------

const {
  data: toolDetail,
  loading: detailLoading,
  failed: detailFailed,
  error: detailError,
  reload: reloadDetail,
} = useAsyncData<Tool | null>(
  () => (selectedToolId.value === '' ? Promise.resolve(null) : getAdminTool(selectedToolId.value)),
  { immediate: false, initial: null },
)

const {
  data: summary,
  loading: summaryLoading,
  failed: summaryFailed,
  error: summaryError,
  reload: reloadSummary,
} = useAsyncData<ToolUsageSummary | null>(
  () => {
    const id = selectedToolId.value
    const range = dateRange.value
    if (id === '' || range === null) {
      return Promise.resolve(null)
    }
    return getUsageSummary(id, range[0], range[1])
  },
  { immediate: false, initial: null },
)

function loadTool(): void {
  if (selectedToolId.value === '') {
    notify.warning('请先选择工具')
    return
  }
  void reloadDetail()
  void reloadSummary()
}

function reloadAll(): void {
  void reloadTools()
  if (selectedToolId.value !== '') {
    loadTool()
  }
}
</script>

<template>
  <div class="tool-version-page">
    <PageHeader title="工具版本" description="查看所选工具的当前版本标识与用量汇总。">
      <template #actions>
        <ElButton @click="reloadAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="warning"
      :closable="false"
      show-icon
      class="tool-version-page__notice"
      title="本页为只读"
      description="后端未提供工具版本的管理端增删改接口（版本 CRUD 尚未实现），本页仅展示工具当前的 current_version_id 与用量汇总。"
    />

    <ElCard shadow="never" class="tool-version-page__filters">
      <ElAlert
        v-if="toolsFailed"
        type="error"
        :closable="false"
        show-icon
        title="工具列表加载失败"
        :description="toolsError?.message ?? '请稍后重试'"
        class="tool-version-page__alert"
      />
      <p v-if="toolsFailed && toolsError?.traceId" class="tool-version-page__trace">
        Trace ID: {{ toolsError.traceId }}
      </p>
      <ElSpace wrap>
        <ElSelect
          v-model="selectedToolId"
          :loading="toolsLoading"
          placeholder="请选择工具"
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
        <ElDatePicker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
        />
        <ElButton type="primary" @click="loadTool">查询</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never">
      <DataStateView
        :loading="detailLoading"
        :failed="detailFailed"
        :error="detailError"
        :empty="toolDetail === null"
        empty-text="请选择工具以查看版本与用量信息"
        @retry="loadTool"
      >
        <ElDescriptions v-if="toolDetail" :column="2" border>
          <ElDescriptionsItem v-if="!fields.isHidden('code')" label="Code">
            {{ toolDetail.code }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('name')" label="名称">
            {{ toolDetail.name }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('slug')" label="Slug">
            {{ toolDetail.slug }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('current_version_id')" label="当前版本 ID">
            {{ toolDetail.current_version_id ?? '未设置' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('execution_mode')" label="执行方式">
            <StatusTag :value="toolDetail.execution_mode" :labels="TOOL_MODE_LABEL" />
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('status')" label="状态">
            <StatusTag :value="toolDetail.status" />
          </ElDescriptionsItem>
        </ElDescriptions>

        <div class="tool-version-page__section">
          <h4 class="tool-version-page__section-title">用量汇总</h4>
          <DataStateView
            :loading="summaryLoading"
            :failed="summaryFailed"
            :error="summaryError"
            :empty="summary === null"
            empty-text="暂无用量数据"
            @retry="reloadSummary"
          >
            <div v-if="summary" class="tool-version-page__stats">
              <StatCard
                label="总调用次数"
                :value="formatNumber(summary.total_executions)"
                :hint="`${summary.period_start} ~ ${summary.period_end}`"
              />
              <StatCard label="成功" :value="formatNumber(summary.success_count)" />
              <StatCard label="失败" :value="formatNumber(summary.failure_count)" />
              <StatCard label="独立用户" :value="formatNumber(summary.unique_users)" />
              <StatCard label="平均耗时" :value="formatDuration(summary.avg_duration_ms)" />
            </div>
          </DataStateView>
        </div>
      </DataStateView>
    </ElCard>
  </div>
</template>

<style scoped>
.tool-version-page__notice {
  margin-bottom: 16px;
}

.tool-version-page__filters {
  margin-bottom: 16px;
}

.tool-version-page__alert {
  margin-bottom: 12px;
}

.tool-version-page__trace {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.tool-version-page__section {
  margin-top: 20px;
}

.tool-version-page__section-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
}

.tool-version-page__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}
</style>
