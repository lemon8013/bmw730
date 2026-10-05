<script setup lang="ts">
/** 角色管理：角色 CRUD、权限分配与角色继承。 */
import { computed, nextTick, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
  ElTree,
  type FormRules,
  type TreeData,
  type TreeInstance,
} from 'element-plus'

import { fetchPermissionTree } from '@/api/permissions'
import {
  assignRoleParents,
  assignRolePermissions,
  createRole,
  deleteRole,
  getRoleParents,
  getRolePermissions,
  listRoles,
  updateRole,
} from '@/api/roles'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { MAX_PAGE_SIZE, usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import { DATA_SCOPE, DATA_SCOPE_LABEL, type DataScopeValue } from '@/types/enums'
import type {
  CreateRoleRequest,
  ParentRoleBrief,
  PermissionTreeNode,
  Role,
  UpdateRoleRequest,
} from '@/types/system'
import { renderError, type RenderedError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.roleView)

/** 是否具备任一角色管理动作的权限。 */
const canManage = computed(() =>
  permission.any([
    PERMISSION.roleEdit,
    PERMISSION.roleDelete,
    PERMISSION.rolePermissionEdit,
    PERMISSION.roleInheritEdit,
  ]),
)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function dataScopeLabel(scope: string): string {
  return DATA_SCOPE_LABEL[scope as DataScopeValue] ?? scope
}

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

// ---------------------------------------------------------------------------
// 角色列表
// ---------------------------------------------------------------------------

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listRoles(page.value, pageSize.value),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

/** 供角色继承下拉使用的全量角色。 */
const { data: allRoles, reload: reloadAllRoles } = useAsyncData(() => listRoles(1, MAX_PAGE_SIZE))

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

// ---------------------------------------------------------------------------
// 角色表单
// ---------------------------------------------------------------------------

interface RoleFormModel {
  role_code: string
  role_name: string
  description: string
  status: string
  data_scope: string
}

const formModel = reactive<RoleFormModel>({
  role_code: '',
  role_name: '',
  description: '',
  status: 'ACTIVE',
  data_scope: 'ALL',
})

const rules: FormRules = {
  role_code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
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
  formModel.role_code = ''
  formModel.role_name = ''
  formModel.description = ''
  formModel.status = 'ACTIVE'
  formModel.data_scope = 'ALL'
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const role = row as unknown as Role
  editingId.value = role.id
  formModel.role_code = role.role_code
  formModel.role_name = role.role_name
  formModel.description = role.description ?? ''
  formModel.status = role.status
  formModel.data_scope = role.data_scope
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
      const payload: CreateRoleRequest = {
        role_code: formModel.role_code,
        role_name: formModel.role_name,
        description: description === '' ? null : description,
        data_scope: formModel.data_scope,
      }
      await createRole(payload)
      notify.success('角色已创建')
    } else {
      const payload: UpdateRoleRequest = {
        role_name: formModel.role_name,
        description: description === '' ? null : description,
        status: formModel.status,
        data_scope: formModel.data_scope,
      }
      await updateRole(editingId.value, payload)
      notify.success('角色已更新')
    }
    dialogVisible.value = false
    await reload()
    await reloadAllRoles()
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

async function onToggleStatus(row: Record<string, unknown>): Promise<void> {
  const role = row as unknown as Role
  const nextStatus = role.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  if (nextStatus === 'DISABLED') {
    const confirmed = await notify.confirm({
      title: '禁用角色',
      message: `确定要禁用角色「${role.role_name}」吗？持有该角色的账号将失去其授予的权限。`,
      danger: true,
    })
    if (!confirmed) {
      return
    }
  }
  try {
    await updateRole(role.id, { status: nextStatus })
    notify.success(nextStatus === 'ACTIVE' ? '角色已启用' : '角色已禁用')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const role = row as unknown as Role
  const confirmed = await notify.confirm({
    title: '删除角色',
    message: `确定要删除角色「${role.role_name}」吗？该操作不可撤销。`,
    danger: true,
    requireTypedText: role.role_code,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteRole(role.id)
    notify.success('角色已删除')
    await reload()
    await reloadAllRoles()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 权限分配
// ---------------------------------------------------------------------------

const {
  data: permissionTreeNodes,
  isEmpty: permissionTreeEmpty,
  reload: reloadPermissionTree,
} = useAsyncData(() => fetchPermissionTree())

const permissionTreeData = computed(
  () => (permissionTreeNodes.value ?? []) as unknown as TreeData,
)

const permissionTreeProps = { label: 'permission_name', children: 'children' }

/** 收集已物化的全部节点 key。 */
function collectTreeKeys(nodes: readonly PermissionTreeNode[]): string[] {
  const keys: string[] = []
  const walk = (list: readonly PermissionTreeNode[]): void => {
    for (const node of list) {
      keys.push(node.id)
      if (node.children !== undefined && node.children.length > 0) {
        walk(node.children)
      }
    }
  }
  walk(nodes)
  return keys
}

/** 收集已物化的叶子节点 key，用于「反选」。 */
function collectLeafKeys(nodes: readonly PermissionTreeNode[]): string[] {
  const keys: string[] = []
  const walk = (list: readonly PermissionTreeNode[]): void => {
    for (const node of list) {
      if (node.children !== undefined && node.children.length > 0) {
        walk(node.children)
      } else {
        keys.push(node.id)
      }
    }
  }
  walk(nodes)
  return keys
}

/**
 * 全选 / 反选 / 全部取消。
 *
 * 权限树由 `fetchPermissionTree()` 一次性取回，并配合 `default-expand-all` 在挂载时
 * 展开全部节点，因此这里遍历的是**已物化的所有节点**而非只勾选根节点——即使使用者
 * 看到的是折叠状态，隐藏的后代也会一并被勾选。若将来改成惰性加载，需要先预加载
 * （`lazy` + `load`）把全部节点物化，再执行下面同样的遍历。
 */
async function checkAllPermissions(): Promise<void> {
  await nextTick()
  const tree = permissionTreeRef.value
  if (tree === undefined) {
    return
  }
  tree.setCheckedKeys(collectTreeKeys(permissionTreeNodes.value ?? []))
}

async function invertPermissions(): Promise<void> {
  await nextTick()
  const tree = permissionTreeRef.value
  if (tree === undefined) {
    return
  }
  const checkedLeaves = new Set(tree.getCheckedKeys(true).map((key) => String(key)))
  tree.setCheckedKeys(
    collectLeafKeys(permissionTreeNodes.value ?? []).filter((key) => !checkedLeaves.has(key)),
  )
}

async function clearPermissions(): Promise<void> {
  await nextTick()
  permissionTreeRef.value?.setCheckedKeys([])
}

const permissionsVisible = ref(false)
const permissionsLoading = ref(false)
const permissionsSaving = ref(false)
const permissionsError = ref<RenderedError | null>(null)
const permissionTreeRef = ref<TreeInstance>()
const activeRole = ref<Role | null>(null)

async function loadPermissions(role: Role): Promise<void> {
  permissionsLoading.value = true
  permissionsError.value = null
  try {
    await reloadPermissionTree()
    const briefs = await getRolePermissions(role.id)
    permissionsLoading.value = false
    await nextTick()
    permissionTreeRef.value?.setCheckedKeys(briefs.map((brief) => brief.id))
  } catch (caught) {
    permissionsError.value = renderError(caught)
  } finally {
    permissionsLoading.value = false
  }
}

function openPermissions(row: Record<string, unknown>): void {
  const role = row as unknown as Role
  activeRole.value = role
  permissionsVisible.value = true
  void loadPermissions(role)
}

function retryPermissions(): void {
  const role = activeRole.value
  if (role !== null) {
    void loadPermissions(role)
  }
}

async function savePermissions(): Promise<void> {
  const role = activeRole.value
  if (role === null) {
    return
  }
  const checked = permissionTreeRef.value?.getCheckedKeys(true) ?? []
  const halfChecked = permissionTreeRef.value?.getHalfCheckedKeys() ?? []
  const ids = [...checked, ...halfChecked].map((key) => String(key))
  permissionsSaving.value = true
  permissionsError.value = null
  try {
    await assignRolePermissions(role.id, { permission_ids: ids })
    notify.success('角色权限已保存')
    permissionsVisible.value = false
  } catch (caught) {
    permissionsError.value = renderError(caught)
  } finally {
    permissionsSaving.value = false
  }
}

// ---------------------------------------------------------------------------
// 角色继承
// ---------------------------------------------------------------------------

const inheritanceVisible = ref(false)
const inheritanceSaving = ref(false)
const inheritanceError = ref<RenderedError | null>(null)
const parentIds = ref<string[]>([])
/** 当前角色已继承的父角色，带有后端返回的名称。 */
const parentBriefs = ref<ParentRoleBrief[]>([])

/**
 * 可选父角色：排除自身。
 *
 * 已选中的父角色即使不在全量列表里（例如超过一页），也要用后端返回的名称补上，
 * 否则下拉框只会显示原始 id。
 */
const parentOptions = computed(() => {
  const current = activeRole.value
  const options = (allRoles.value?.items ?? [])
    .filter((role) => role.id !== current?.id)
    .map((role) => ({ id: role.id, label: `${role.role_name}（${role.role_code}）` }))
  const known = new Set(options.map((option) => option.id))
  for (const brief of parentBriefs.value) {
    if (brief.id === current?.id || known.has(brief.id)) {
      continue
    }
    options.push({ id: brief.id, label: `${brief.role_name}（${brief.role_code}）` })
    known.add(brief.id)
  }
  return options
})

async function loadInheritance(role: Role): Promise<void> {
  inheritanceError.value = null
  try {
    if (allRoles.value === null) {
      await reloadAllRoles()
    }
    const parents = await getRoleParents(role.id)
    parentBriefs.value = parents
    parentIds.value = parents.map((parent) => parent.id)
  } catch (caught) {
    inheritanceError.value = renderError(caught)
  }
}

function openInheritance(row: Record<string, unknown>): void {
  const role = row as unknown as Role
  activeRole.value = role
  parentIds.value = []
  parentBriefs.value = []
  inheritanceVisible.value = true
  void loadInheritance(role)
}

function retryInheritance(): void {
  const role = activeRole.value
  if (role !== null) {
    void loadInheritance(role)
  }
}

async function saveInheritance(): Promise<void> {
  const role = activeRole.value
  if (role === null) {
    return
  }
  inheritanceSaving.value = true
  inheritanceError.value = null
  try {
    await assignRoleParents(role.id, { parent_role_ids: [...parentIds.value] })
    notify.success('角色继承已保存')
    inheritanceVisible.value = false
  } catch (caught) {
    inheritanceError.value = renderError(caught)
  } finally {
    inheritanceSaving.value = false
  }
}
</script>

<template>
  <div class="role-page">
    <PageHeader title="角色管理" description="维护角色、分配权限并配置角色继承关系。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-permission="PERMISSION.roleCreate" type="primary" @click="openCreate">
          新建角色
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无角色"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('role_code')"
          prop="role_code"
          label="角色编码"
          min-width="150"
        />
        <ElTableColumn
          v-if="!fields.isHidden('role_name')"
          prop="role_name"
          label="角色名称"
          min-width="140"
        />
        <ElTableColumn v-if="!fields.isHidden('data_scope')" label="数据范围" width="140">
          <template #default="{ row }">{{ dataScopeLabel(row.data_scope) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="96">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('user_count')" label="用户数" width="90">
          <template #default="{ row }">{{ row.user_count ?? 0 }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('description')"
          prop="description"
          label="描述"
          min-width="180"
          show-overflow-tooltip
        />
        <ElTableColumn label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canManage" label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton
                v-permission="PERMISSION.roleEdit"
                link
                type="primary"
                @click="openEdit(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-permission="PERMISSION.rolePermissionEdit"
                link
                type="primary"
                @click="openPermissions(row)"
              >
                分配权限
              </ElButton>
              <ElButton
                v-permission="PERMISSION.roleInheritEdit"
                link
                type="primary"
                @click="openInheritance(row)"
              >
                角色继承
              </ElButton>
              <ElButton
                v-permission="PERMISSION.roleEdit"
                link
                :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
                @click="onToggleStatus(row)"
              >
                {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
              </ElButton>
              <ElButton
                v-permission="PERMISSION.roleDelete"
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
      :title="editingId === null ? '新建角色' : '编辑角色'"
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
        <ElFormItem v-if="!fields.isHidden('role_code')" label="角色编码" prop="role_code">
          <ElInput
            v-model="formModel.role_code"
            :disabled="editingId !== null || fields.isReadOnly('role_code')"
            placeholder="例如 OPS_ADMIN"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('role_name')" label="角色名称" prop="role_name">
          <ElInput v-model="formModel.role_name" :disabled="fields.isReadOnly('role_name')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('data_scope')" label="数据范围">
          <ElSelect v-model="formModel.data_scope" :disabled="fields.isReadOnly('data_scope')">
            <ElOption
              v-for="item in DATA_SCOPE"
              :key="item"
              :label="dataScopeLabel(item)"
              :value="item"
            />
          </ElSelect>
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
      </BaseForm>
    </BaseDialog>

    <BaseDialog
      v-model="permissionsVisible"
      :title="activeRole ? `分配权限：${activeRole.role_name}` : '分配权限'"
      :confirm-loading="permissionsSaving"
      width="640px"
      @confirm="savePermissions"
    >
      <DataStateView
        :loading="permissionsLoading"
        :failed="permissionsError !== null"
        :error="permissionsError"
        :empty="permissionTreeEmpty"
        empty-text="暂无可分配的权限"
        @retry="retryPermissions"
      >
        <div class="role-page__tree-actions">
          <ElButton size="small" @click="checkAllPermissions">全选</ElButton>
          <ElButton size="small" @click="invertPermissions">反选</ElButton>
          <ElButton size="small" @click="clearPermissions">全部取消</ElButton>
        </div>
        <ElTree
          ref="permissionTreeRef"
          :data="permissionTreeData"
          :props="permissionTreeProps"
          node-key="id"
          show-checkbox
          default-expand-all
        />
      </DataStateView>
    </BaseDialog>

    <BaseDialog
      v-model="inheritanceVisible"
      :title="activeRole ? `角色继承：${activeRole.role_name}` : '角色继承'"
      :confirm-loading="inheritanceSaving"
      @confirm="saveInheritance"
    >
      <p class="role-page__hint">选择要继承的父角色，子角色将同时拥有父角色授予的权限。</p>
      <DataStateView
        :loading="false"
        :failed="inheritanceError !== null"
        :error="inheritanceError"
        :empty="false"
        @retry="retryInheritance"
      >
        <ElSelect v-model="parentIds" multiple placeholder="选择父角色" style="width: 100%">
          <ElOption
            v-for="option in parentOptions"
            :key="option.id"
            :label="option.label"
            :value="option.id"
          />
        </ElSelect>
      </DataStateView>
    </BaseDialog>
  </div>
</template>

<style scoped>
.role-page__hint {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.role-page__tree-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
