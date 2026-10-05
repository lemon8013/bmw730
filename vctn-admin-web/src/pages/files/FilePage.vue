<script setup lang="ts">
/**
 * 文件管理：查看已登记的文件元数据，登记新对象元数据并做逻辑删除。
 * 后端未提供预签名 / 上传完成 / 下载端点，本页不触碰服务器文件系统。
 * 删除操作需要 SYSTEM_FILE_MANAGE 权限。
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import { createFileRecord, deleteFile, listFiles } from '@/api/files'
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
import type { FileCreateRequest, FileRecord } from '@/types/ops'
import { FILE_STATUS, STATUS_LABEL } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatBytes, formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.systemFileManage)

/** 是否具备文件管理权限。 */
const canManage = computed(() => permission.has(PERMISSION.systemFileManage))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function statusLabel(value: string): string {
  return STATUS_LABEL[value] ?? value
}

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const status = ref('')
const ownerType = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listFiles({
    status: status.value === '' ? undefined : status.value,
    owner_type: ownerType.value.trim() === '' ? undefined : ownerType.value.trim(),
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
  ownerType.value = ''
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
// 登记文件元数据
// ---------------------------------------------------------------------------

interface FileFormModel {
  storage_provider: string
  bucket: string
  object_key: string
  original_name: string
  content_type: string
  size_bytes: number | null
  checksum: string
  owner_type: string
  owner_id: number | null
  metadata: string
}

const formModel = reactive<FileFormModel>({
  storage_provider: '',
  bucket: '',
  object_key: '',
  original_name: '',
  content_type: '',
  size_bytes: null,
  checksum: '',
  owner_type: '',
  owner_id: null,
  metadata: '',
})

const rules: FormRules = {
  object_key: [{ required: true, message: '请输入对象存储 Key', trigger: 'blur' }],
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
  formModel.storage_provider = ''
  formModel.bucket = ''
  formModel.object_key = ''
  formModel.original_name = ''
  formModel.content_type = ''
  formModel.size_bytes = null
  formModel.checksum = ''
  formModel.owner_type = ''
  formModel.owner_id = null
  formModel.metadata = ''
  clearSubmitError()
  dialogVisible.value = true
}

/** 将 metadata 文本解析为 JSON 对象；空文本返回 null。 */
function parseMetadata(text: string): Record<string, unknown> | null {
  const trimmed = text.trim()
  if (trimmed === '') {
    return null
  }
  const parsed: unknown = JSON.parse(trimmed)
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('metadata 必须是 JSON 对象')
  }
  return parsed as Record<string, unknown>
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()

  let metadata: Record<string, unknown> | null
  try {
    metadata = parseMetadata(formModel.metadata)
  } catch (caught) {
    submitError.value = caught instanceof Error ? caught.message : 'metadata 解析失败'
    return
  }

  submitting.value = true
  try {
    const provider = formModel.storage_provider.trim()
    const payload: FileCreateRequest = {
      storage_provider: provider === '' ? undefined : provider,
      bucket: emptyToNull(formModel.bucket),
      object_key: formModel.object_key,
      original_name: emptyToNull(formModel.original_name),
      content_type: emptyToNull(formModel.content_type),
      size_bytes: formModel.size_bytes,
      checksum: emptyToNull(formModel.checksum),
      owner_type: emptyToNull(formModel.owner_type),
      owner_id: formModel.owner_id,
      metadata,
    }
    await createFileRecord(payload)
    notify.success('文件元数据已登记')
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

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const file = row as unknown as FileRecord
  const confirmed = await notify.confirm({
    title: '删除文件记录',
    message: `确定要删除文件记录「${file.object_key}」吗？该操作仅做逻辑删除。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteFile(file.id)
    notify.success('文件记录已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="file-page">
    <PageHeader title="文件管理" description="查看并登记对象存储中的文件元数据；删除需要 SYSTEM_FILE_MANAGE 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.systemFileManage"
          type="primary"
          @click="openCreate"
        >
          登记文件元数据
        </ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      title="上传 / 下载接口未实现"
      description="后端未提供预签名、上传完成与下载端点，因此本页不提供上传或下载控件，也不会直接读写服务器文件系统。"
      class="file-page__notice"
    />

    <ElCard shadow="never" class="file-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="ownerType"
          placeholder="按归属类型筛选"
          clearable
          style="width: 200px"
          @keyup.enter="onSearch"
        />
        <ElSelect v-model="status" placeholder="状态" clearable style="width: 160px">
          <ElOption
            v-for="item in FILE_STATUS"
            :key="item"
            :label="statusLabel(item)"
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
        empty-text="暂无文件记录"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('object_key')"
          prop="object_key"
          label="对象 Key"
          min-width="220"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('original_name')"
          prop="original_name"
          label="原始文件名"
          min-width="180"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('content_type')"
          prop="content_type"
          label="内容类型"
          width="150"
        />
        <ElTableColumn v-if="!fields.isHidden('size_bytes')" label="大小" width="110">
          <template #default="{ row }">{{ formatBytes(row.size_bytes) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('storage_provider')"
          prop="storage_provider"
          label="存储提供方"
          width="130"
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canManage" label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton
              v-permission="PERMISSION.systemFileManage"
              link
              type="danger"
              @click="onDelete(row)"
            >
              删除
            </ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      title="登记文件元数据"
      :confirm-loading="submitting"
      width="640px"
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
        <ElFormItem v-if="!fields.isHidden('object_key')" label="对象 Key" prop="object_key">
          <ElInput
            v-model="formModel.object_key"
            :disabled="fields.isReadOnly('object_key')"
            placeholder="已存储对象的 Key"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('storage_provider')" label="存储提供方">
          <ElInput
            v-model="formModel.storage_provider"
            :disabled="fields.isReadOnly('storage_provider')"
            placeholder="可选，例如 LOCAL / S3"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('bucket')" label="Bucket">
          <ElInput v-model="formModel.bucket" :disabled="fields.isReadOnly('bucket')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('original_name')" label="原始文件名">
          <ElInput
            v-model="formModel.original_name"
            :disabled="fields.isReadOnly('original_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('content_type')" label="内容类型">
          <ElInput
            v-model="formModel.content_type"
            :disabled="fields.isReadOnly('content_type')"
            placeholder="例如 image/png"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('size_bytes')" label="大小（字节）">
          <ElInputNumber
            v-model="formModel.size_bytes"
            :min="0"
            :disabled="fields.isReadOnly('size_bytes')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('checksum')" label="校验和">
          <ElInput v-model="formModel.checksum" :disabled="fields.isReadOnly('checksum')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('owner_type')" label="归属类型">
          <ElInput v-model="formModel.owner_type" :disabled="fields.isReadOnly('owner_type')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('owner_id')" label="归属 ID">
          <ElInputNumber
            v-model="formModel.owner_id"
            :min="0"
            :disabled="fields.isReadOnly('owner_id')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('metadata')" label="元数据（JSON）">
          <ElInput
            v-model="formModel.metadata"
            type="textarea"
            :rows="4"
            :disabled="fields.isReadOnly('metadata')"
            placeholder='例如 {"source":"upload"}'
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.file-page__notice {
  margin-bottom: 16px;
}

.file-page__filters {
  margin-bottom: 16px;
}
</style>
