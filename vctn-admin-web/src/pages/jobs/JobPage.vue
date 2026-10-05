<script setup lang="ts">
/**
 * 作业管理：查看系统作业并重试失败作业。
 * 重试操作需要 SYSTEM_JOB_MANAGE 权限。后端未实现取消接口，页面不提供取消动作。
 */
import { computed, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
} from 'element-plus'

import { listJobs, retryJob } from '@/api/jobs'
import PageHeader from '@/components/common/PageHeader.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type { SystemJob } from '@/types/ops'
import { JOB_STATUS, JOB_STATUS_LABEL } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.systemJobManage)

/** 是否具备作业管理权限。 */
const canManage = computed(() => permission.has(PERMISSION.systemJobManage))

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
// 列表与筛选
// ---------------------------------------------------------------------------

const status = ref('')
const jobType = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listJobs({
    status: status.value === '' ? undefined : status.value,
    job_type: jobType.value.trim() === '' ? undefined : jobType.value.trim(),
    page: page.value,
    page_size: pageSize.value,
  }),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

function onSearch(): void {
  changePage(1)
  void reload()
}

function onReset(): void {
  status.value = ''
  jobType.value = ''
  changePage(1)
  void reload()
}

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

// ---------------------------------------------------------------------------
// 重试
// ---------------------------------------------------------------------------

async function onRetry(row: Record<string, unknown>): Promise<void> {
  const job = row as unknown as SystemJob
  const confirmed = await notify.confirm({
    title: '重试作业',
    message: `确定要重试作业「${job.job_name}」吗？`,
  })
  if (!confirmed) {
    return
  }
  try {
    await retryJob(job.id)
    notify.success('作业已重新入队')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detail = ref<SystemJob | null>(null)

function openDetail(row: Record<string, unknown>): void {
  detail.value = row as unknown as SystemJob
  detailVisible.value = true
}
</script>

<template>
  <div class="job-page">
    <PageHeader title="作业管理" description="查看系统作业执行情况并重试；重试需要 SYSTEM_JOB_MANAGE 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="warning"
      :closable="false"
      show-icon
      title="取消接口暂未实现"
      description="后端未提供作业取消端点，因此本页不提供取消操作。"
      class="job-page__notice"
    />

    <ElCard shadow="never" class="job-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="jobType"
          placeholder="按作业类型筛选"
          clearable
          style="width: 200px"
          @keyup.enter="onSearch"
        />
        <ElSelect v-model="status" placeholder="状态" clearable style="width: 160px">
          <ElOption
            v-for="item in JOB_STATUS"
            :key="item"
            :label="JOB_STATUS_LABEL[item]"
            :value="item"
          />
        </ElSelect>
        <ElButton type="primary" @click="onSearch">查询</ElButton>
        <ElButton @click="onReset">重置</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无作业"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn v-if="!fields.isHidden('job_code')" prop="job_code" label="作业编码" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('job_name')" prop="job_name" label="作业名称" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('job_type')" prop="job_type" label="类型" width="130" />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" :labels="JOB_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('priority')" prop="priority" label="优先级" width="90" />
        <ElTableColumn
          v-if="!fields.isHidden('attempt_count')"
          prop="attempt_count"
          label="尝试次数"
          width="100"
        />
        <ElTableColumn v-if="!fields.isHidden('available_at')" label="可执行时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.available_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('finished_at')" label="完成时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.finished_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
              <ElButton
                v-if="canManage"
                v-permission="PERMISSION.systemJobManage"
                link
                type="warning"
                @click="onRetry(row)"
              >
                重试
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog v-model="detailVisible" title="作业详情" width="720px" hide-footer>
      <template v-if="detail">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="作业编码">{{ detail.job_code }}</ElDescriptionsItem>
          <ElDescriptionsItem label="作业名称">{{ detail.job_name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="类型">{{ detail.job_type }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <StatusTag :value="detail.status" :labels="JOB_STATUS_LABEL" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="优先级">{{ detail.priority }}</ElDescriptionsItem>
          <ElDescriptionsItem label="尝试次数">
            {{ detail.attempt_count }} / {{ detail.max_attempts }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="可执行时间">
            {{ formatDateTime(detail.available_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="完成时间">
            {{ formatDateTime(detail.finished_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间" :span="2">
            {{ formatDateTime(detail.created_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>
        <h4 class="job-page__section-title">最后错误</h4>
        <pre class="job-page__error">{{ detail.last_error ?? '—' }}</pre>
        <h4 class="job-page__section-title">Payload</h4>
        <JsonViewer :value="detail.payload ?? null" />
      </template>
    </BaseDialog>
  </div>
</template>

<style scoped>
.job-page__notice {
  margin-bottom: 16px;
}

.job-page__filters {
  margin-bottom: 16px;
}

.job-page__section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.job-page__error {
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background-color: var(--el-fill-color-light);
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
