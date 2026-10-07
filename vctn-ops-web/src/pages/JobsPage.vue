<script setup lang="ts">
/**
 * Job runs.
 *
 * Retrying and stopping are high risk: the backend validates that the run's
 * current status allows the action and writes the audit record, so an
 * impossible request is refused instead of silently mutating the row. The
 * console still asks first, and only offers the action the status allows.
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

import { fetchJobStatistics, listJobs, retryJob, stopJob } from '@/api/ops/jobs'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatCard from '@/components/charts/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import {
  JOB_STATUS,
  RETRYABLE_JOB_STATUSES,
  STOPPABLE_JOB_STATUSES,
} from '@/types/enums'
import type { JobRun } from '@/types/ops'
import { formatDateTime, formatDuration, formatPercent } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.jobManage))

const filters = ref({
  status: '',
  definitionCode: '',
  range: null as [string, string] | null,
})

const list = usePagedList<JobRun>((page, pageSize) =>
  listJobs(page, pageSize, {
    status: filters.value.status === '' ? undefined : filters.value.status,
    definitionCode:
      filters.value.definitionCode.trim() === '' ? undefined : filters.value.definitionCode.trim(),
    startAt: filters.value.range?.[0] ?? null,
    endAt: filters.value.range?.[1] ?? null,
  }),
)

void list.reload()

const statisticsDays = ref(7)
const statistics = useAsyncData(() => fetchJobStatistics(statisticsDays.value))

const canRetry = (row: JobRun): boolean => RETRYABLE_JOB_STATUSES.includes(row.status)
const canStop = (row: JobRun): boolean => STOPPABLE_JOB_STATUSES.includes(row.status)

async function retry(row: JobRun): Promise<void> {
  const confirmed = await confirmAction({
    title: '重试作业',
    message: `确定重新执行作业「${row.job_name}」？`,
    confirmText: '重试',
  })
  if (!confirmed) {
    return
  }
  try {
    await retryJob(row.id)
    ElMessage.success('作业已重新排队')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

async function stop(row: JobRun): Promise<void> {
  const confirmed = await confirmAction({
    title: '停止作业',
    message: `确定停止作业「${row.job_name}」？正在执行的部分将被中断。`,
    confirmText: '停止',
  })
  if (!confirmed) {
    return
  }
  try {
    await stopJob(row.id)
    ElMessage.success('作业已停止')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="作业监控" description="作业执行的成功率、耗时与手动干预" />

    <div class="vctn-panel">
      <div class="jobs__stats-header">
        <h3 class="vctn-section-title">执行统计</h3>
        <ElSelect
          v-model="statisticsDays"
          class="jobs__days"
          @change="statistics.reload()"
        >
          <ElOption :value="1" label="近 1 天" />
          <ElOption :value="7" label="近 7 天" />
          <ElOption :value="30" label="近 30 天" />
        </ElSelect>
      </div>

      <p v-if="statistics.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="statistics.failed.value" class="vctn-muted">
        {{ statistics.error.value ?? '统计加载失败' }}
      </p>
      <div v-else-if="statistics.data.value" class="jobs__stats">
        <StatCard label="总数" :value="statistics.data.value.total" />
        <StatCard label="成功" :value="statistics.data.value.success_count" />
        <StatCard label="失败" :value="statistics.data.value.failed_count" />
        <StatCard label="连续失败" :value="statistics.data.value.consecutive_failed_count" />
        <StatCard
          label="成功率"
          :value="formatPercent(statistics.data.value.success_rate)"
        />
        <StatCard
          label="平均耗时"
          :value="formatDuration(statistics.data.value.avg_duration_seconds)"
        />
      </div>
    </div>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElSelect v-model="filters.status" placeholder="状态" clearable class="jobs__field">
          <ElOption v-for="status in JOB_STATUS" :key="status" :value="status" :label="status" />
        </ElSelect>
        <ElInput
          v-model="filters.definitionCode"
          placeholder="作业定义编码"
          clearable
          class="jobs__definition"
          @keyup.enter="list.search()"
        />
        <ElDatePicker
          v-model="filters.range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="jobs__range"
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
      empty-text="没有匹配的作业"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="job_code" label="作业编码" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="job_name" label="作业名称" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="job_type" label="类型" width="110" />
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }"><StatusTag :value="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn label="尝试" width="100">
        <template #default="{ row }">{{ row.attempt_count }} / {{ row.max_attempts }}</template>
      </ElTableColumn>
      <ElTableColumn label="耗时" width="130">
        <template #default="{ row }">{{ formatDuration(row.duration_seconds) }}</template>
      </ElTableColumn>
      <ElTableColumn label="开始时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="last_error" label="最近错误" min-width="200" show-overflow-tooltip />

      <template #operations="{ row }">
        <ElButton
          v-if="canManage && canRetry(row)"
          link
          type="warning"
          @click="retry(row)"
        >
          重试
        </ElButton>
        <ElButton v-if="canManage && canStop(row)" link type="danger" @click="stop(row)">
          停止
        </ElButton>
      </template>
    </BaseTable>
  </div>
</template>

<style scoped>
.jobs__stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.jobs__days {
  width: 130px;
}

.jobs__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--vctn-space-4);
}

.jobs__field {
  width: 140px;
}

.jobs__definition {
  width: 180px;
}

.jobs__range {
  width: 360px;
}
</style>
