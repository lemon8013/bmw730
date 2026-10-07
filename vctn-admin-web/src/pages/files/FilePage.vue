<script setup lang="ts">
/**
 * 文件管理：上传、下载与删除。
 *
 * 上传分两步：先向后端申请一个存放位置（对象存储如 RustFS 返回预签名直传地址，
 * 本地存储走 API 代理），再把字节体 PUT/POST 上去；直传结束后必须确认一次，
 * 否则后端会回收那条“有名无实”的记录。所有操作都需要 SYSTEM_FILE_MANAGE 权限。
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

import {
  confirmUpload,
  createFileRecord,
  createUploadIntent,
  deleteFile,
  getDownloadUrl,
  listFiles,
  proxiedContentUrl,
  uploadFileContent,
} from '@/api/files'
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

// ---------------------------------------------------------------------------
// 上传
// ---------------------------------------------------------------------------

const uploadVisible = ref(false)
const uploadBusy = ref(false)
const uploadError = ref<string | null>(null)
const uploadFileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const uploadCategory = ref('general')

function openUpload(): void {
  selectedFile.value = null
  uploadCategory.value = 'general'
  uploadError.value = null
  if (uploadFileInput.value) {
    uploadFileInput.value.value = ''
  }
  uploadVisible.value = true
}

function pickFile(event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
  uploadError.value = null
}

async function submitUpload(): Promise<void> {
  const file = selectedFile.value
  if (!file) {
    uploadError.value = '请先选择要上传的文件'
    return
  }
  uploadBusy.value = true
  uploadError.value = null
  try {
    const intent = await createUploadIntent({
      original_name: file.name,
      content_type: file.type === '' ? undefined : file.type,
      category: uploadCategory.value.trim() === '' ? 'general' : uploadCategory.value.trim(),
      size_bytes: file.size,
    })
    await uploadFileContent(intent, file, intent.content_type)
    // 直传由浏览器完成，后端没有参与，必须回来确认字节真的落到了对象存储。
    if (intent.mode === 'direct') {
      await confirmUpload(intent.id)
    }
    notify.success(intent.mode === 'direct' ? '文件已上传至对象存储' : '文件已上传')
    uploadVisible.value = false
    await reload()
  } catch (caught) {
    uploadError.value = failureText(caught)
  } finally {
    uploadBusy.value = false
  }
}

/** 下载：对象存储返回临时签名地址；本地存储只能由后端代理输出。 */
async function onDownload(row: Record<string, unknown>): Promise<void> {
  const file = row as unknown as FileRecord
  try {
    const result = await getDownloadUrl(file.id, false)
    const target = result.url ?? proxiedContentUrl(file.id)
    window.open(target, '_blank', 'noopener')
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const file = row as unknown as FileRecord
  const confirmed = await notify.confirm({
    title: '删除文件',
    message: `确定要删除「${file.original_name ?? file.object_key}」吗？对象本体与记录都会被移除（记录为逻辑删除）。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteFile(file.id)
    notify.success('文件已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="file-page">
    <PageHeader
      title="文件管理"
      description="上传文件到对象存储（RustFS / S3），查看已登记的文件元数据并下载或删除。所有操作需要 SYSTEM_FILE_MANAGE 权限。"
    >
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.systemFileManage"
          type="primary"
          plain
          @click="openCreate"
        >
          登记元数据
        </ElButton>
        <ElButton
          v-permission="PERMISSION.systemFileManage"
          type="primary"
          @click="openUpload"
        >
          上传文件
        </ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      title="对象存储由后端统一承载"
      description="文件一经上传就写入后端配置的对象存储：S3 兼容模式（RustFS 等）下浏览器直传预签名地址，仅在本地存储模式下由后端代理。对象的 Key、类型与大小由后端核定，前端无法指定。"
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
        <ElTableColumn v-if="canManage" label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <ElSpace :size="4">
              <ElButton
                v-permission="PERMISSION.systemFileManage"
                link
                type="primary"
                @click="onDownload(row)"
              >
                下载
              </ElButton>
              <ElButton
                v-permission="PERMISSION.systemFileManage"
                link
                type="danger"
                @click="onDelete(row)"
              >
                删除
              </ElButton>
            </ElSpace>
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

    <BaseDialog
      v-model="uploadVisible"
      title="上传文件"
      confirm-text="开始上传"
      :confirm-loading="uploadBusy"
      width="560px"
      @confirm="submitUpload"
    >
      <ElAlert
        v-if="uploadError"
        type="error"
        :closable="false"
        show-icon
        :title="uploadError"
        class="file-page__upload-error"
      />
      <ElFormItem label="文件">
        <input ref="uploadFileInput" type="file" @change="pickFile" />
        <div v-if="selectedFile" class="file-page__picked">
          {{ selectedFile.name }}
          <span class="file-page__picked-size">（{{ formatBytes(selectedFile.size) }}）</span>
        </div>
      </ElFormItem>
      <ElFormItem label="分类目录">
        <ElSelect v-model="uploadCategory" style="width: 200px">
          <ElOption label="general（通用）" value="general" />
          <ElOption label="avatar（头像）" value="avatar" />
          <ElOption label="image（图片）" value="image" />
          <ElOption label="attachment（附件）" value="attachment" />
          <ElOption label="export（导出）" value="export" />
        </ElSelect>
      </ElFormItem>
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

.file-page__picked {
  margin-top: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.file-page__picked-size {
  color: var(--el-text-color-secondary);
}

.file-page__upload-error {
  margin-bottom: 16px;
}
</style>
