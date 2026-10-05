<script setup lang="ts">
/** 权限管理：顶部在「树形结构 / 列表」之间切换，详情与增删改都在对话框中完成。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElTabPane,
  ElTabs,
  ElTable,
  ElTableColumn,
  ElTree,
  type FormRules,
  type TreeData,
} from 'element-plus'

import {
  createPermissionResource,
  deletePermissionResource,
  fetchPermissionTree,
  listPermissionResources,
  updatePermissionResource,
} from '@/api/permissions'
import DataStateView from '@/components/common/DataStateView.vue'
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
import {
  FIELD_MODE,
  FIELD_MODE_LABEL,
  PERMISSION_TYPE,
  PERMISSION_TYPE_LABEL,
  type PermissionType,
} from '@/types/enums'
import type {
  CreateResourceRequest,
  FieldPermissionInput,
  PermissionResource,
  PermissionTreeNode,
  UpdateResourceRequest,
} from '@/types/system'
import { renderError } from '@/utils/error'

const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.permissionView)

/** 顶部页签：树形结构在前，扁平列表在后。 */
const activeTab = ref<'tree' | 'list'>('tree')

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

/** 权限类型标签；未知值原样显示，方便发现后端新增的类型。 */
function permissionTypeLabel(value: string | null): string {
  if (value === null || value === '') {
    return '—'
  }
  return PERMISSION_TYPE_LABEL[value as PermissionType] ?? value
}

/** 字段权限模式标签。 */
function fieldModeLabel(mode: string): string {
  return FIELD_MODE_LABEL[mode as keyof typeof FIELD_MODE_LABEL] ?? mode
}

/** 从结构化的行记录中安全读取字符串字段。 */
function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key]
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return null
}

/** 从结构化的行记录中安全读取数字字段。 */
function readNumber(source: Record<string, unknown>, key: string): number {
  const value = source[key]
  return typeof value === 'number' ? value : 0
}

const treeProps = { label: 'permission_name', children: 'children' }

// ---------------------------------------------------------------------------
// 权限树
// ---------------------------------------------------------------------------

const {
  data: treeNodes,
  loading: treeLoading,
  failed: treeFailed,
  error: treeError,
  reload: reloadTree,
} = useAsyncData(() => fetchPermissionTree())

const treeData = computed(() => (treeNodes.value ?? []) as unknown as TreeData)

/**
 * 最近一次在树中点选的节点。
 *
 * 点击节点会打开详情对话框，同时记住它，作为「新建权限资源」时的默认上级。
 */
const selectedNode = ref<PermissionTreeNode | null>(null)

function onNodeClick(node: Record<string, unknown>): void {
  const treeNode = node as unknown as PermissionTreeNode
  selectedNode.value = treeNode
  openDetail(node)
}

/** 父级下拉选项：把权限树按层级展开。 */
const parentOptions = computed(() => {
  const options: { value: string; label: string }[] = []
  const walk = (nodes: PermissionTreeNode[], depth: number): void => {
    for (const node of nodes) {
      options.push({ value: node.id, label: `${'　'.repeat(depth)}${node.permission_name}` })
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1)
      }
    }
  }
  walk(treeNodes.value ?? [], 0)
  return options
})

/** 在已加载的权限树中把上级 id 解析为名称。 */
function parentLabel(parentId: string | null): string {
  if (parentId === null || parentId === '') {
    return '—'
  }
  const match = parentOptions.value.find((option) => option.value === parentId)
  return match === undefined ? '未知上级资源' : match.label.trim()
}

// ---------------------------------------------------------------------------
// 权限资源列表
// ---------------------------------------------------------------------------

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listPermissionResources(page.value, pageSize.value),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

function refreshAll(): void {
  void reloadTree()
  void reload()
}

// ---------------------------------------------------------------------------
// 详情对话框
// ---------------------------------------------------------------------------

/** 详情对话框使用的规范化视图，兼容树节点与列表行两种来源。 */
interface ResourceDetail {
  permission_code: string | null
  permission_name: string | null
  permission_type: string | null
  resource_type: string | null
  resource_code: string | null
  parent_id: string | null
  path: string | null
  method: string | null
  status: string | null
  sort_order: number
  description: string | null
  field_permissions: FieldPermRow[]
}

const detailVisible = ref(false)
const detail = ref<ResourceDetail | null>(null)

function readFieldPerms(source: Record<string, unknown>): FieldPermRow[] {
  const value = source.field_permissions
  if (!Array.isArray(value)) {
    return []
  }
  const items: FieldPermRow[] = []
  for (const entry of value) {
    if (typeof entry !== 'object' || entry === null) {
      continue
    }
    const record = entry as Record<string, unknown>
    const fieldCode = readString(record, 'field_code')
    const fieldMode = readString(record, 'field_mode')
    if (fieldCode !== null && fieldMode !== null) {
      items.push({ field_code: fieldCode, field_mode: fieldMode })
    }
  }
  return items
}

/** 打开详情对话框；树节点缺少的字段（如 field_permissions）留空即可。 */
function openDetail(row: Record<string, unknown>): void {
  detail.value = {
    permission_code: readString(row, 'permission_code'),
    permission_name: readString(row, 'permission_name'),
    permission_type: readString(row, 'permission_type'),
    resource_type: readString(row, 'resource_type'),
    resource_code: readString(row, 'resource_code'),
    parent_id: readString(row, 'parent_id'),
    path: readString(row, 'path'),
    method: readString(row, 'method'),
    status: readString(row, 'status'),
    sort_order: readNumber(row, 'sort_order'),
    description: readString(row, 'description'),
    field_permissions: readFieldPerms(row),
  }
  detailVisible.value = true
}

// ---------------------------------------------------------------------------
// 字段权限编辑行
// ---------------------------------------------------------------------------

type FieldPermRow = { field_code: string; field_mode: string }

const fieldPermRows = ref<FieldPermRow[]>([])

function addFieldPerm(): void {
  fieldPermRows.value.push({ field_code: '', field_mode: 'VISIBLE' })
}

function removeFieldPerm(index: number): void {
  fieldPermRows.value.splice(index, 1)
}

function collectFieldPerms(): FieldPermissionInput[] {
  return fieldPermRows.value
    .filter((row) => row.field_code.trim() !== '')
    .map((row) => ({ field_code: row.field_code.trim(), field_mode: row.field_mode }))
}

// ---------------------------------------------------------------------------
// 新建 / 编辑资源
// ---------------------------------------------------------------------------

interface ResourceFormModel {
  permission_code: string
  permission_name: string
  permission_type: string
  resource_type: string
  resource_code: string
  parent_id: string | null
  sort_order: number
  status: string
  description: string
}

const formModel = reactive<ResourceFormModel>({
  permission_code: '',
  permission_name: '',
  permission_type: 'PAGE',
  resource_type: 'PAGE',
  resource_code: '',
  parent_id: null,
  sort_order: 0,
  status: 'ACTIVE',
  description: '',
})

const rules: FormRules = {
  permission_code: [{ required: true, message: '请输入权限编码', trigger: 'blur' }],
  permission_name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }],
  resource_code: [{ required: true, message: '请输入资源编码', trigger: 'blur' }],
}

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openCreate(): void {
  editingId.value = null
  formModel.permission_code = ''
  formModel.permission_name = ''
  formModel.permission_type = 'PAGE'
  formModel.resource_type = 'PAGE'
  formModel.resource_code = ''
  formModel.parent_id = selectedNode.value?.id ?? null
  formModel.sort_order = 0
  formModel.status = 'ACTIVE'
  formModel.description = ''
  fieldPermRows.value = []
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const resource = row as unknown as PermissionResource
  editingId.value = resource.id
  formModel.permission_code = resource.permission_code
  formModel.permission_name = resource.permission_name
  formModel.permission_type = resource.permission_type
  formModel.resource_type = resource.resource_type
  formModel.resource_code = resource.resource_code
  formModel.parent_id = resource.parent_id ?? null
  formModel.sort_order = resource.sort_order
  formModel.status = resource.status
  formModel.description = resource.description ?? ''
  fieldPermRows.value = (resource.field_permissions ?? []).map((entry) => ({
    field_code: entry.field_code,
    field_mode: entry.field_mode,
  }))
  clearSubmitError()
  dialogVisible.value = true
}

function reportSubmitError(caught: unknown): void {
  const rendered = renderError(caught)
  submitError.value = rendered.message
  submitTrace.value = rendered.traceId ?? null
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    const description = formModel.description.trim()
    if (editingId.value === null) {
      const payload: CreateResourceRequest = {
        permission_code: formModel.permission_code,
        permission_name: formModel.permission_name,
        permission_type: formModel.permission_type,
        resource_type: formModel.resource_type,
        resource_code: formModel.resource_code,
        parent_id: formModel.parent_id,
        sort_order: formModel.sort_order,
        description: description === '' ? null : description,
        field_permissions: collectFieldPerms(),
      }
      await createPermissionResource(payload)
      notify.success('权限资源已创建')
    } else {
      const payload: UpdateResourceRequest = {
        permission_name: formModel.permission_name,
        resource_type: formModel.resource_type,
        resource_code: formModel.resource_code,
        parent_id: formModel.parent_id,
        sort_order: formModel.sort_order,
        status: formModel.status,
        description: description === '' ? null : description,
        field_permissions: collectFieldPerms(),
      }
      await updatePermissionResource(editingId.value, payload)
      notify.success('权限资源已更新')
    }
    dialogVisible.value = false
    await reload()
    await reloadTree()
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const resource = row as unknown as PermissionResource
  const confirmed = await notify.confirm({
    title: '删除权限资源',
    message: `确定要删除「${resource.permission_name}」吗？其字段权限配置也会一并移除，该操作不可撤销。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deletePermissionResource(resource.id)
    notify.success('权限资源已删除')
    await reload()
    await reloadTree()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="permission-page">
    <PageHeader title="权限管理" description="维护权限资源树以及每个资源上的字段级权限。">
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.permissionResourceEdit"
          type="primary"
          @click="openCreate"
        >
          新建权限资源
        </ElButton>
      </template>
    </PageHeader>

    <ElTabs v-model="activeTab" type="border-card">
      <ElTabPane label="树形结构" name="tree">
        <DataStateView
          :loading="treeLoading"
          :failed="treeFailed"
          :error="treeError"
          :empty="treeData.length === 0"
          empty-text="暂无权限树数据"
          @retry="reloadTree"
        >
          <ElTree
            :data="treeData"
            :props="treeProps"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="onNodeClick"
          />
        </DataStateView>
      </ElTabPane>

      <ElTabPane label="列表" name="list">
        <BaseTable
          :rows="rows"
          :loading="loading"
          :failed="failed"
          :error="error"
          :total="total"
          :page="page"
          :page-size="pageSize"
          empty-text="暂无权限资源"
          @retry="reload"
          @update:page="onPageChange"
          @update:page-size="onPageSizeChange"
        >
          <ElTableColumn
            v-if="!fields.isHidden('permission_code')"
            prop="permission_code"
            label="权限编码"
            min-width="160"
          />
          <ElTableColumn
            v-if="!fields.isHidden('permission_name')"
            prop="permission_name"
            label="权限名称"
            min-width="140"
          />
          <ElTableColumn
            v-if="!fields.isHidden('permission_type')"
            prop="permission_type"
            label="权限类型"
            width="110"
          >
            <template #default="{ row }">{{ permissionTypeLabel(row.permission_type) }}</template>
          </ElTableColumn>
          <ElTableColumn
            v-if="!fields.isHidden('resource_type')"
            prop="resource_type"
            label="资源类型"
            width="110"
          >
            <template #default="{ row }">{{ permissionTypeLabel(row.resource_type) }}</template>
          </ElTableColumn>
          <ElTableColumn
            v-if="!fields.isHidden('resource_code')"
            prop="resource_code"
            label="资源编码"
            min-width="140"
          />
          <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="96">
            <template #default="{ row }">
              <StatusTag :value="row.status" />
            </template>
          </ElTableColumn>
          <ElTableColumn v-if="!fields.isHidden('sort_order')" prop="sort_order" label="排序" width="80" />
          <ElTableColumn label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <ElSpace>
                <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
                <ElButton
                  v-permission="PERMISSION.permissionResourceEdit"
                  link
                  type="primary"
                  @click="openEdit(row)"
                >
                  编辑
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.permissionResourceEdit"
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
      </ElTabPane>
    </ElTabs>

    <BaseDialog v-model="detailVisible" title="权限资源详情" width="720px" hide-footer>
      <ElDescriptions v-if="detail" :column="2" border>
        <ElDescriptionsItem label="权限编码">{{ detail.permission_code ?? '—' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="权限名称">{{ detail.permission_name ?? '—' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="权限类型">
          {{ permissionTypeLabel(detail.permission_type) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="资源类型">
          {{ permissionTypeLabel(detail.resource_type) }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="资源编码">{{ detail.resource_code ?? '—' }}</ElDescriptionsItem>
        <ElDescriptionsItem label="上级资源">{{ parentLabel(detail.parent_id) }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="detail.path" label="路径">{{ detail.path }}</ElDescriptionsItem>
        <ElDescriptionsItem v-if="detail.method" label="请求方法">
          {{ detail.method }}
        </ElDescriptionsItem>
        <ElDescriptionsItem label="状态">
          <StatusTag :value="detail.status" />
        </ElDescriptionsItem>
        <ElDescriptionsItem label="排序">{{ detail.sort_order }}</ElDescriptionsItem>
        <ElDescriptionsItem label="描述" :span="2">{{ detail.description ?? '—' }}</ElDescriptionsItem>
      </ElDescriptions>

      <div class="permission-page__detail-fields">
        <h4 class="permission-page__detail-title">字段权限</h4>
        <ElTable
          :data="detail?.field_permissions ?? []"
          border
          size="small"
          empty-text="暂无字段权限"
        >
          <ElTableColumn prop="field_code" label="字段编码" min-width="180" />
          <ElTableColumn label="模式" width="120">
            <template #default="{ row }">{{ fieldModeLabel(row.field_mode) }}</template>
          </ElTableColumn>
        </ElTable>
      </div>
    </BaseDialog>

    <BaseDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建权限资源' : '编辑权限资源'"
      :confirm-loading="submitting"
      width="720px"
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
        <ElFormItem
          v-if="!fields.isHidden('permission_code')"
          label="权限编码"
          prop="permission_code"
        >
          <ElInput
            v-model="formModel.permission_code"
            :disabled="editingId !== null || fields.isReadOnly('permission_code')"
            placeholder="例如 USER_CREATE"
          />
        </ElFormItem>
        <ElFormItem
          v-if="!fields.isHidden('permission_name')"
          label="权限名称"
          prop="permission_name"
        >
          <ElInput
            v-model="formModel.permission_name"
            :disabled="fields.isReadOnly('permission_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('permission_type')" label="权限类型">
          <ElSelect
            v-model="formModel.permission_type"
            :disabled="editingId !== null || fields.isReadOnly('permission_type')"
          >
            <ElOption
              v-for="item in PERMISSION_TYPE"
              :key="item"
              :label="PERMISSION_TYPE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('resource_type')" label="资源类型">
          <ElSelect v-model="formModel.resource_type" :disabled="fields.isReadOnly('resource_type')">
            <ElOption
              v-for="item in PERMISSION_TYPE"
              :key="item"
              :label="PERMISSION_TYPE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem
          v-if="!fields.isHidden('resource_code')"
          label="资源编码"
          prop="resource_code"
        >
          <ElInput
            v-model="formModel.resource_code"
            :disabled="fields.isReadOnly('resource_code')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('parent_id')" label="上级资源">
          <ElSelect
            v-model="formModel.parent_id"
            clearable
            :disabled="fields.isReadOnly('parent_id')"
            placeholder="不选表示顶级资源"
          >
            <ElOption
              v-for="item in parentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('sort_order')" label="排序">
          <ElInputNumber
            v-model="formModel.sort_order"
            :min="0"
            :disabled="fields.isReadOnly('sort_order')"
          />
        </ElFormItem>
        <ElFormItem v-if="editingId !== null && !fields.isHidden('status')" label="状态">
          <ElSelect v-model="formModel.status" :disabled="fields.isReadOnly('status')">
            <ElOption label="启用" value="ACTIVE" />
            <ElOption label="禁用" value="DISABLED" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="formModel.description"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>

        <ElFormItem v-if="!fields.isHidden('field_permissions')" label="字段权限">
          <div class="permission-page__field-editor">
            <ElTable :data="fieldPermRows" border size="small">
              <ElTableColumn label="字段编码" min-width="180">
                <template #default="{ row }">
                  <ElInput
                    v-model="row.field_code"
                    placeholder="字段编码，例如 email"
                    :disabled="fields.isReadOnly('field_permissions')"
                  />
                </template>
              </ElTableColumn>
              <ElTableColumn label="模式" width="160">
                <template #default="{ row }">
                  <ElSelect
                    v-model="row.field_mode"
                    :disabled="fields.isReadOnly('field_permissions')"
                  >
                    <ElOption
                      v-for="mode in FIELD_MODE"
                      :key="mode"
                      :label="FIELD_MODE_LABEL[mode]"
                      :value="mode"
                    />
                  </ElSelect>
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="80">
                <template #default="{ $index }">
                  <ElButton
                    link
                    type="danger"
                    :disabled="fields.isReadOnly('field_permissions')"
                    @click="removeFieldPerm($index)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
            <ElButton
              link
              type="primary"
              :disabled="fields.isReadOnly('field_permissions')"
              @click="addFieldPerm"
            >
              添加字段权限
            </ElButton>
          </div>
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.permission-page__detail-fields {
  margin-top: 16px;
}

.permission-page__detail-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.permission-page__field-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
</style>
