<script setup lang="ts">
/**
 * 字典管理：整页展示字典类型列表，点击字典编码在弹窗中维护该类型下的字典项。
 *
 * 类型与字典项分属两层：类型走分页路由表格，字典项数量有限且从属于某个类型，
 * 因此在类型行展开的弹窗里直接维护，避免为二层数据再开一条路由。
 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElEmpty,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElSwitch,
  ElTable,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import {
  createDictItem,
  createDictType,
  deleteDictItem,
  deleteDictType,
  listDictItems,
  listDictTypes,
  updateDictItem,
  updateDictType,
} from '@/api/dictionaries'
import { ApiError } from '@/api/errors'
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
import { ERROR_CODE } from '@/types/api'
import { ACTIVE_STATUS, STATUS_LABEL } from '@/types/enums'
import type {
  CreateDictItemRequest,
  CreateDictTypeRequest,
  DictItem,
  DictType,
  UpdateDictItemRequest,
  UpdateDictTypeRequest,
} from '@/types/system'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.dictView)

/** 是否具备字典编辑权限。 */
const canEdit = computed(() => permission.has(PERMISSION.dictEdit))

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

/** 冲突（同类型同值唯一约束）：HTTP 409 或后端 conflict 语义码。 */
function isConflict(caught: unknown): boolean {
  return (
    caught instanceof ApiError &&
    (caught.httpStatus === 409 || caught.code === ERROR_CODE.conflict)
  )
}

// ---------------------------------------------------------------------------
// 字典类型列表
// ---------------------------------------------------------------------------

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listDictTypes(page.value, pageSize.value),
)

const typeRows = computed(() => asRows(data.value?.items ?? []))

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

// ---------------------------------------------------------------------------
// 字典项（在弹窗内维护，非分页路由）
// ---------------------------------------------------------------------------

/** 当前弹窗所对应的字典类型。 */
const itemsType = ref<DictType | null>(null)
const itemsVisible = ref(false)

const {
  data: itemData,
  loading: itemLoading,
  failed: itemFailed,
  error: itemError,
  reload: reloadItems,
} = useAsyncData(
  () =>
    itemsType.value === null
      ? Promise.resolve<DictItem[]>([])
      : listDictItems(itemsType.value.id),
  { immediate: false },
)

const itemRows = computed<DictItem[]>(() => itemData.value ?? [])

const itemsTitle = computed(() =>
  itemsType.value === null
    ? '字典项'
    : `字典项：${itemsType.value.dict_name}（${itemsType.value.dict_code}）`,
)

const itemsMetaText = computed(() =>
  itemsType.value === null ? '' : `共 ${itemRows.value.length} 个字典项`,
)

/** 打开某个类型的字典项弹窗并加载其字典项。 */
function openItems(row: Record<string, unknown>): void {
  itemsType.value = row as unknown as DictType
  clearSubmitError()
  itemsVisible.value = true
  void reloadItems()
}

/** 字典项变更后：刷新弹窗内列表，并刷新类型列表以保持字典项数量准确。 */
async function refreshAfterItemChange(): Promise<void> {
  await reloadItems()
  await reload()
}

// ---------------------------------------------------------------------------
// 提交错误
// ---------------------------------------------------------------------------

const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

/**
 * 写入提交失败信息。
 *
 * 409 语义（同一字典类型下字典值唯一）由调用方给出专属文案，不会被吞成
 * 通用错误；其余失败统一走 `renderError`。
 */
function reportSubmitError(caught: unknown, conflictMessage: string): void {
  if (isConflict(caught)) {
    const rendered = renderError(caught)
    submitError.value = conflictMessage
    submitTrace.value = rendered.traceId ?? null
    return
  }
  const rendered = renderError(caught)
  submitError.value = rendered.message
  submitTrace.value = rendered.traceId ?? null
}

// ---------------------------------------------------------------------------
// 字典类型表单
// ---------------------------------------------------------------------------

interface TypeFormModel {
  dict_code: string
  dict_name: string
  status: string
  description: string
}

const typeModel = reactive<TypeFormModel>({
  dict_code: '',
  dict_name: '',
  status: 'ACTIVE',
  description: '',
})

const typeRules: FormRules = {
  dict_code: [{ required: true, message: '请输入字典编码', trigger: 'blur' }],
  dict_name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
}

const typeDialogVisible = ref(false)
const editingTypeId = ref<string | null>(null)
const typeSubmitting = ref(false)
const typeFormRef = ref<InstanceType<typeof BaseForm>>()

function openCreateType(): void {
  editingTypeId.value = null
  typeModel.dict_code = ''
  typeModel.dict_name = ''
  typeModel.status = 'ACTIVE'
  typeModel.description = ''
  clearSubmitError()
  typeDialogVisible.value = true
}

function openEditType(row: Record<string, unknown>): void {
  const type = row as unknown as DictType
  editingTypeId.value = type.id
  typeModel.dict_code = type.dict_code
  typeModel.dict_name = type.dict_name
  typeModel.status = type.status
  typeModel.description = type.description ?? ''
  clearSubmitError()
  typeDialogVisible.value = true
}

async function submitType(): Promise<void> {
  const valid = await typeFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()
  typeSubmitting.value = true
  try {
    if (editingTypeId.value === null) {
      const payload: CreateDictTypeRequest = {
        dict_code: typeModel.dict_code,
        dict_name: typeModel.dict_name,
        description: typeModel.description.trim() === '' ? null : typeModel.description.trim(),
      }
      await createDictType(payload)
      notify.success('字典类型已创建')
    } else {
      const payload: UpdateDictTypeRequest = {
        dict_name: typeModel.dict_name,
        status: typeModel.status,
        description: typeModel.description.trim() === '' ? null : typeModel.description.trim(),
      }
      await updateDictType(editingTypeId.value, payload)
      notify.success('字典类型已更新')
    }
    typeDialogVisible.value = false
    await reload()
  } catch (caught) {
    reportSubmitError(caught, '该字典编码已存在，请更换后重试')
  } finally {
    typeSubmitting.value = false
  }
}

async function onToggleTypeStatus(row: Record<string, unknown>): Promise<void> {
  const type = row as unknown as DictType
  const nextStatus = type.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  if (nextStatus === 'DISABLED') {
    const confirmed = await notify.confirm({
      title: '禁用字典类型',
      message: `确定要禁用「${type.dict_name}」吗？该类型下的字典项将不再对业务生效。`,
      danger: true,
    })
    if (!confirmed) {
      return
    }
  }
  try {
    await updateDictType(type.id, { status: nextStatus })
    notify.success(nextStatus === 'ACTIVE' ? '字典类型已启用' : '字典类型已禁用')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDeleteType(row: Record<string, unknown>): Promise<void> {
  const type = row as unknown as DictType
  const confirmed = await notify.confirm({
    title: '删除字典类型',
    message: `确定要删除「${type.dict_name}」吗？该操作不可撤销。`,
    danger: true,
    requireTypedText: type.dict_code,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteDictType(type.id)
    notify.success('字典类型已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 字典项表单（在字典项弹窗之上打开）
// ---------------------------------------------------------------------------

interface ItemFormModel {
  item_label: string
  item_value: string
  item_code: string
  sort_order: number
  is_default: boolean
  status: string
  description: string
}

const itemModel = reactive<ItemFormModel>({
  item_label: '',
  item_value: '',
  item_code: '',
  sort_order: 0,
  is_default: false,
  status: 'ACTIVE',
  description: '',
})

const itemRules: FormRules = {
  item_label: [{ required: true, message: '请输入字典标签', trigger: 'blur' }],
  item_value: [{ required: true, message: '请输入字典值', trigger: 'blur' }],
}

const itemDialogVisible = ref(false)
const editingItemId = ref<string | null>(null)
const itemSubmitting = ref(false)
const itemFormRef = ref<InstanceType<typeof BaseForm>>()

function openCreateItem(): void {
  if (itemsType.value === null) {
    notify.warning('请先选择字典类型')
    return
  }
  editingItemId.value = null
  itemModel.item_label = ''
  itemModel.item_value = ''
  itemModel.item_code = ''
  itemModel.sort_order = 0
  itemModel.is_default = false
  itemModel.status = 'ACTIVE'
  itemModel.description = ''
  clearSubmitError()
  itemDialogVisible.value = true
}

function openEditItem(row: Record<string, unknown>): void {
  const item = row as unknown as DictItem
  editingItemId.value = item.id
  itemModel.item_label = item.item_label
  itemModel.item_value = item.item_value
  itemModel.item_code = item.item_code ?? ''
  itemModel.sort_order = item.sort_order
  itemModel.is_default = item.is_default
  itemModel.status = item.status
  itemModel.description = item.description ?? ''
  clearSubmitError()
  itemDialogVisible.value = true
}

async function submitItem(): Promise<void> {
  if (itemsType.value === null) {
    notify.warning('请先选择字典类型')
    return
  }
  const valid = await itemFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()
  itemSubmitting.value = true
  try {
    if (editingItemId.value === null) {
      const payload: CreateDictItemRequest = {
        item_label: itemModel.item_label,
        item_value: itemModel.item_value,
        item_code: itemModel.item_code.trim() === '' ? null : itemModel.item_code.trim(),
        sort_order: itemModel.sort_order,
        is_default: itemModel.is_default,
        description: itemModel.description.trim() === '' ? null : itemModel.description.trim(),
      }
      await createDictItem(itemsType.value.id, payload)
      notify.success('字典项已创建')
    } else {
      const payload: UpdateDictItemRequest = {
        item_label: itemModel.item_label,
        item_value: itemModel.item_value,
        item_code: itemModel.item_code.trim() === '' ? null : itemModel.item_code.trim(),
        sort_order: itemModel.sort_order,
        is_default: itemModel.is_default,
        status: itemModel.status,
        description: itemModel.description.trim() === '' ? null : itemModel.description.trim(),
      }
      await updateDictItem(editingItemId.value, payload)
      notify.success('字典项已更新')
    }
    itemDialogVisible.value = false
    await refreshAfterItemChange()
  } catch (caught) {
    reportSubmitError(caught, '同一字典类型下，字典值必须唯一，请更换字典值')
  } finally {
    itemSubmitting.value = false
  }
}

async function onSetDefault(row: Record<string, unknown>): Promise<void> {
  const item = row as unknown as DictItem
  try {
    await updateDictItem(item.id, { is_default: !item.is_default })
    notify.success(item.is_default ? '已取消默认' : '已设为默认')
    await refreshAfterItemChange()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onToggleItemStatus(row: Record<string, unknown>): Promise<void> {
  const item = row as unknown as DictItem
  const nextStatus = item.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  if (nextStatus === 'DISABLED') {
    const confirmed = await notify.confirm({
      title: '禁用字典项',
      message: `确定要禁用「${item.item_label}」吗？`,
      danger: true,
    })
    if (!confirmed) {
      return
    }
  }
  try {
    await updateDictItem(item.id, { status: nextStatus })
    notify.success(nextStatus === 'ACTIVE' ? '字典项已启用' : '字典项已禁用')
    await refreshAfterItemChange()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDeleteItem(row: Record<string, unknown>): Promise<void> {
  const item = row as unknown as DictItem
  const confirmed = await notify.confirm({
    title: '删除字典项',
    message: `确定要删除「${item.item_label}」吗？该操作不可撤销。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteDictItem(item.id)
    notify.success('字典项已删除')
    await refreshAfterItemChange()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="dictionary-page">
    <PageHeader title="字典管理" description="维护系统枚举值：字典类型与类型下的字典项。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-permission="PERMISSION.dictEdit" type="primary" @click="openCreateType">
          新建字典类型
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never">
      <BaseTable
        :rows="typeRows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无字典类型"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('dict_code')"
          label="字典编码"
          min-width="190"
        >
          <template #default="{ row }">
            <ElButton
              link
              type="primary"
              class="dictionary-page__code"
              @click="openItems(row)"
            >
              {{ row.dict_code }}
            </ElButton>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('dict_name')"
          prop="dict_name"
          label="字典名称"
          min-width="150"
        />
        <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="96">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('description')"
          label="描述"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">{{ row.description ?? '—' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('item_count')" label="字典项数" width="100">
          <template #default="{ row }">{{ row.item_count ?? 0 }}</template>
        </ElTableColumn>
        <ElTableColumn label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canEdit" label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton link type="primary" @click="openItems(row)">字典项</ElButton>
              <ElButton
                v-permission="PERMISSION.dictEdit"
                link
                type="primary"
                @click="openEditType(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-permission="PERMISSION.dictEdit"
                link
                :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
                @click="onToggleTypeStatus(row)"
              >
                {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
              </ElButton>
              <ElButton
                v-permission="PERMISSION.dictEdit"
                link
                type="danger"
                @click="onDeleteType(row)"
              >
                删除
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog v-model="itemsVisible" :title="itemsTitle" width="820px" hide-footer>
      <div class="dictionary-page__items">
        <div class="dictionary-page__items-toolbar">
          <span class="dictionary-page__items-meta">{{ itemsMetaText }}</span>
          <ElButton
            v-if="canEdit"
            v-permission="PERMISSION.dictEdit"
            type="primary"
            size="small"
            @click="openCreateItem"
          >
            新建字典项
          </ElButton>
        </div>

        <template v-if="itemFailed">
          <ElAlert
            type="error"
            :closable="false"
            show-icon
            title="字典项加载失败"
            :description="itemError?.message ?? '请稍后重试'"
          />
          <div class="dictionary-page__items-retry">
            <ElButton type="primary" @click="reloadItems">重试</ElButton>
            <span v-if="itemError?.traceId" class="dictionary-page__trace">
              Trace ID: {{ itemError.traceId }}
            </span>
          </div>
        </template>

        <ElTable
          v-else
          v-loading="itemLoading"
          :data="itemRows"
          row-key="id"
          border
          stripe
          class="dictionary-page__items-table"
        >
          <ElTableColumn
            v-if="!fields.isHidden('item_label')"
            prop="item_label"
            label="标签"
            min-width="140"
          />
          <ElTableColumn
            v-if="!fields.isHidden('item_value')"
            prop="item_value"
            label="值"
            min-width="120"
          />
          <ElTableColumn
            v-if="!fields.isHidden('sort_order')"
            prop="sort_order"
            label="排序"
            width="80"
          />
          <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="92">
            <template #default="{ row }">
              <StatusTag :value="row.status" />
            </template>
          </ElTableColumn>
          <ElTableColumn v-if="!fields.isHidden('is_default')" label="默认" width="86">
            <template #default="{ row }">
              <StatusTag :value="row.is_default" :boolean-labels="['否', '是']" />
            </template>
          </ElTableColumn>
          <ElTableColumn v-if="canEdit" label="操作" width="250" fixed="right">
            <template #default="{ row }">
              <ElSpace wrap>
                <ElButton
                  v-permission="PERMISSION.dictEdit"
                  link
                  type="primary"
                  @click="openEditItem(row)"
                >
                  编辑
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.dictEdit"
                  link
                  type="primary"
                  @click="onSetDefault(row)"
                >
                  {{ row.is_default ? '取消默认' : '设为默认' }}
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.dictEdit"
                  link
                  :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
                  @click="onToggleItemStatus(row)"
                >
                  {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.dictEdit"
                  link
                  type="danger"
                  @click="onDeleteItem(row)"
                >
                  删除
                </ElButton>
              </ElSpace>
            </template>
          </ElTableColumn>
          <template #empty>
            <ElEmpty :description="itemLoading ? '加载中…' : '该类型下暂无字典项'" />
          </template>
        </ElTable>
      </div>
    </BaseDialog>

    <BaseDialog
      v-model="typeDialogVisible"
      :title="editingTypeId === null ? '新建字典类型' : '编辑字典类型'"
      :confirm-loading="typeSubmitting"
      @confirm="submitType"
    >
      <BaseForm
        ref="typeFormRef"
        :model="typeModel"
        :rules="typeRules"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem
          v-if="!fields.isHidden('dict_code')"
          label="字典编码"
          prop="dict_code"
        >
          <ElInput
            v-model="typeModel.dict_code"
            :disabled="editingTypeId !== null || fields.isReadOnly('dict_code')"
            placeholder="例如 user_status"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('dict_name')" label="字典名称" prop="dict_name">
          <ElInput v-model="typeModel.dict_name" :disabled="fields.isReadOnly('dict_name')" />
        </ElFormItem>
        <ElFormItem v-if="editingTypeId !== null && !fields.isHidden('status')" label="状态">
          <ElSelect v-model="typeModel.status" :disabled="fields.isReadOnly('status')">
            <ElOption
              v-for="item in ACTIVE_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="typeModel.description"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <BaseDialog
      v-model="itemDialogVisible"
      :title="editingItemId === null ? '新建字典项' : '编辑字典项'"
      :confirm-loading="itemSubmitting"
      @confirm="submitItem"
    >
      <BaseForm
        ref="itemFormRef"
        :model="itemModel"
        :rules="itemRules"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('item_label')" label="字典标签" prop="item_label">
          <ElInput v-model="itemModel.item_label" :disabled="fields.isReadOnly('item_label')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('item_value')" label="字典值" prop="item_value">
          <ElInput v-model="itemModel.item_value" :disabled="fields.isReadOnly('item_value')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('item_code')" label="字典编码">
          <ElInput v-model="itemModel.item_code" :disabled="fields.isReadOnly('item_code')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('sort_order')" label="排序">
          <ElInputNumber
            v-model="itemModel.sort_order"
            :min="0"
            :disabled="fields.isReadOnly('sort_order')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('is_default')" label="默认项">
          <ElSwitch v-model="itemModel.is_default" :disabled="fields.isReadOnly('is_default')" />
        </ElFormItem>
        <ElFormItem v-if="editingItemId !== null && !fields.isHidden('status')" label="状态">
          <ElSelect v-model="itemModel.status" :disabled="fields.isReadOnly('status')">
            <ElOption
              v-for="item in ACTIVE_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="itemModel.description"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.dictionary-page__code {
  font-weight: 600;
  padding: 0;
}

.dictionary-page__items-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.dictionary-page__items-meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.dictionary-page__items-retry {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.dictionary-page__trace {
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
