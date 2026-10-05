<script setup lang="ts">
/**
 * 导出管理：创建导出任务、查看状态并重试。
 * 后端未提供取消与下载端点，本页不提供取消 / 下载动作。
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElStep,
  ElSteps,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import { createExportTask, listExportTasks, retryExportTask } from '@/api/exports'
import PageHeader from '@/components/common/PageHeader.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
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
import type { CreateExportTaskRequest, ExportTask } from '@/types/ops'
import { EXPORT_STATUS, EXPORT_STATUS_LABEL } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime, formatNumber } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.exportView)

/** 是否具备导出管理权限。 */
const canManage = computed(() => permission.has(PERMISSION.exportManage))

/** 导出状态推进的步骤标签。 */
const EXPORT_STEPS = ['待处理', '处理中', '已完成'] as const

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

/** 将导出状态映射到步骤条上的当前步骤。 */
function activeStep(status: string): number {
  if (status === 'SUCCESS') {
    return EXPORT_STEPS.length
  }
  if (status === 'PROCESSING' || status === 'FAILED') {
    return 1
  }
  return 0
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const exportType = ref('')
const status = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listExportTasks({
    export_type: exportType.value.trim() === '' ? undefined : exportType.value.trim(),
    status: status.value === '' ? undefined : status.value,
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
  exportType.value = ''
  status.value = ''
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
// 创建导出任务
// ---------------------------------------------------------------------------

interface ExportFormModel {
  export_type: string
  filter_json: string
}

const formModel = reactive<ExportFormModel>({
  export_type: '',
  filter_json: '',
})

const rules: FormRules = {
  export_type: [{ required: true, message: '请输入导出类型', trigger: 'blur' }],
}

const dialogVisible = ref(false)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openCreate(): void {
  formModel.export_type = ''
  formModel.filter_json = ''
  clearSubmitError()
  dialogVisible.value = true
}

/** 将 filter_json 文本解析为 JSON 对象；空文本返回 null。 */
function parseFilterJson(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  if (trimmed === '') {
    return null
  }
  const parsed: unknown = JSON.parse(trimmed)
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('筛选条件必须是 JSON 对象')
  }
  return parsed as Record<string, unknown>
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()

  let filterJson: Record<string, unknown> | null
  try {
    filterJson = parseFilterJson(formModel.filter_json)
  } catch (caught) {
    submitError.value = caught instanceof Error ? caught.message : '筛选条件解析失败'
    return
  }

  submitting.value = true
  try {
    const payload: CreateExportTaskRequest = {
      export_type: formModel.export_type,
      filter_json: filterJson,
    }
    await createExportTask(payload)
    notify.success('导出任务已创建')
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    const rendered = renderError(caught)
    submitError.value = rendered.message
    submitTrace.value = rendered.traceId ?? null
  } finally {
    submitting.value = false
  }
}

async function onRetry(row: Record<string, unknown>): Promise<void> {
  const task = row as unknown as ExportTask
  const confirmed = await notify.confirm({
    title: '重试导出任务',
    message: `确定要重试该「${task.export_type}」导出任务吗？`,
  })
  if (!confirmed) {
    return
  }
  try {
    await retryExportTask(task.id)
    notify.success('导出任务已重新入队')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 详情
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const selected = ref<ExportTask | null>(null)

function openDetail(row: Record<string, unknown>): void {
  selected.value = row as unknown as ExportTask
  detailVisible.value = true
}
</script>

<template>
  <div class="export-page">
    <PageHeader title="导出管理" description="创建导出任务、跟踪执行状态并重试；导出任务需要 EXPORT_MANAGE 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton
          v-if="canManage"
          v-permission="PERMISSION.exportManage"
          type="primary"
          @click="openCreate"
        >
          新建导出任务
        </ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      title="取消 / 下载接口未实现"
      description="后端未提供导出任务取消与结果下载端点，因此本页不提供取消或下载操作。"
      class="export-page__notice"
    />

    <ElCard shadow="never" class="export-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="exportType"
          placeholder="按导出类型筛选"
          clearable
          style="width: 200px"
          @keyup.enter="onSearch"
        />
        <ElSelect v-model="status" placeholder="状态" clearable style="width: 160px">
          <ElOption
            v-for="item in EXPORT_STATUS"
            :key="item"
            :label="EXPORT_STATUS_LABEL[item]"
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
        empty-text="暂无导出任务"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn v-if="!fields.isHidden('export_type')" prop="export_type" label="导出类型" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" :labels="EXPORT_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('row_count')" label="行数" width="110">
          <template #default="{ row }">{{ formatNumber(row.row_count) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('requested_by')"
          prop="requested_by"
          label="发起人"
          min-width="150"
        />
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('started_at')" label="开始时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
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
                v-permission="PERMISSION.exportManage"
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

    <BaseDialog
      v-model="dialogVisible"
      title="新建导出任务"
      :confirm-loading="submitting"
      @confirm="submit"
    >
      <BaseForm
        ref="formRef"
        :model="formModel"
        :rules="rules"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem label="导出类型" prop="export_type">
          <ElInput v-model="formModel.export_type" placeholder="例如 USER / ORDER" />
        </ElFormItem>
        <ElFormItem label="筛选条件（JSON）">
          <ElInput
            v-model="formModel.filter_json"
            type="textarea"
            :rows="5"
            placeholder='例如 {"status":"ACTIVE"}'
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <BaseDialog v-model="detailVisible" title="导出任务详情" width="720px" hide-footer>
      <template v-if="selected">
        <ElSteps :active="activeStep(selected.status)" align-center finish-status="success" :process-status="selected.status === 'FAILED' ? 'error' : 'process'">
          <ElStep v-for="label in EXPORT_STEPS" :key="label" :title="label" />
        </ElSteps>
        <ElDescriptions :column="2" border class="export-page__detail">
          <ElDescriptionsItem label="导出类型">{{ selected.export_type }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <StatusTag :value="selected.status" :labels="EXPORT_STATUS_LABEL" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="行数">
            {{ formatNumber(selected.row_count) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="发起人">
            {{ selected.requested_by ?? '—' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">
            {{ formatDateTime(selected.created_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="开始时间">
            {{ formatDateTime(selected.started_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="完成时间">
            {{ formatDateTime(selected.finished_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="文件 ID">
            {{ selected.file_id ?? '—' }}
          </ElDescriptionsItem>
        </ElDescriptions>
        <h4 class="export-page__section-title">错误信息</h4>
        <pre class="export-page__error">{{ selected.error_message ?? '—' }}</pre>
        <h4 class="export-page__section-title">筛选条件</h4>
        <JsonViewer :value="selected.filter_json ?? null" />
      </template>
    </BaseDialog>
  </div>
</template>

<style scoped>
.export-page__notice {
  margin-bottom: 16px;
}

.export-page__filters {
  margin-bottom: 16px;
}

.export-page__detail {
  margin-top: 16px;
}

.export-page__section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.export-page__error {
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
