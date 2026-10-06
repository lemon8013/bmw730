<script setup lang="ts">
/** 用户管理：账号 CRUD、角色、部门与密码重置。会话下线入口在在线用户页。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElFormItem,
  ElInput,
  ElOption,
  ElRow,
  ElSelect,
  ElSpace,
  ElTableColumn,
  ElTag,
  ElTooltip,
  type FormRules,
} from 'element-plus'

import { fetchDepartmentTree } from '@/api/departments'
import { listRoles } from '@/api/roles'
import {
  assignUserRoles,
  createUser,
  deleteUser,
  disableUser,
  enableUser,
  getUser,
  getUserRoles,
  getUserSessions,
  listUsers,
  moveUserDepartment,
  resetUserPassword,
  updateUser,
} from '@/api/users'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useClipboard } from '@/composables/useClipboard'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { MAX_PAGE_SIZE, usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import type { ResetPasswordResult } from '@/types/auth'
import { STATUS_LABEL, USER_STATUS } from '@/types/enums'
import type {
  AdminUser,
  CreateUserRequest,
  DepartmentTreeNode,
  UpdateUserRequest,
} from '@/types/system'
import { renderError, type RenderedError } from '@/utils/error'
import { formatDateTime, sameId } from '@/utils/format'

const notify = useConfirm()
const clipboard = useClipboard()
const permission = usePermissionStore()
const auth = useAuthStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.userView)

/** 是否具备任一用户管理动作的权限。 */
const canManage = computed(() =>
  permission.any([PERMISSION.userEdit, PERMISSION.userDelete, PERMISSION.userResetPassword]),
)

/** 禁止对当前登录的超级管理员本人执行的动作提示。 */
const SELF_ACTION_HINT = '不能对当前登录的超级管理员执行该操作'

/** 目标行是否为当前登录的超级管理员本人。 */
function isSelfSuperAdmin(row: Record<string, unknown>): boolean {
  const self = auth.user
  if (self === null || !auth.isSuperAdmin) {
    return false
  }
  if (sameId(String(row.id), self.id)) {
    return true
  }
  return String(row.username) === self.username
}

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toAdminUser(row: Record<string, unknown>): AdminUser {
  return row as unknown as AdminUser
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

const filters = reactive<{
  keyword: string
  department_id: string | undefined
  status: string | undefined
}>({ keyword: '', department_id: undefined, status: undefined })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listUsers({
    keyword: filters.keyword.trim() === '' ? undefined : filters.keyword.trim(),
    department_id: filters.department_id,
    status: filters.status,
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

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

function search(): void {
  changePage(1)
  void reload()
}

function resetFilters(): void {
  filters.keyword = ''
  filters.department_id = undefined
  filters.status = undefined
  search()
}

// ---------------------------------------------------------------------------
// 下拉选项
// ---------------------------------------------------------------------------

const { data: departmentTree } = useAsyncData(() => fetchDepartmentTree())

const departmentOptions = computed(() => {
  const options: { value: string; label: string }[] = []
  const walk = (nodes: DepartmentTreeNode[], depth: number): void => {
    for (const node of nodes) {
      options.push({ value: node.id, label: `${'　'.repeat(depth)}${node.department_name}` })
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1)
      }
    }
  }
  walk(departmentTree.value ?? [], 0)
  return options
})

/** 角色下拉选项：值为角色 id，展示为角色中文名。 */
interface RoleOption {
  value: string
  label: string
}

const { data: rolesPage, reload: reloadRoles } = useAsyncData(() => listRoles(1, MAX_PAGE_SIZE))
const roleOptions = computed<RoleOption[]>(() =>
  (rolesPage.value?.items ?? []).map((role) => ({ value: role.id, label: role.role_name })),
)

// ---------------------------------------------------------------------------
// 通用对话框状态
// ---------------------------------------------------------------------------

const activeUser = ref<AdminUser | null>(null)
const dialogError = ref<RenderedError | null>(null)

function toMessages(): { message: string | null; traceId: string | null } {
  return {
    message: dialogError.value?.message ?? null,
    traceId: dialogError.value?.traceId ?? null,
  }
}

// ---------------------------------------------------------------------------
// 新建用户
// ---------------------------------------------------------------------------

interface CreateUserFormModel {
  username: string
  display_name: string
  email: string
  phone: string
  department_id: string | null
  role_ids: string[]
  temporary_password: string
}

const createModel = reactive<CreateUserFormModel>({
  username: '',
  display_name: '',
  email: '',
  phone: '',
  department_id: null,
  role_ids: [],
  temporary_password: '',
})

const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
}

const createVisible = ref(false)
const createSubmitting = ref(false)
const createFormRef = ref<InstanceType<typeof BaseForm>>()

function openCreate(): void {
  createModel.username = ''
  createModel.display_name = ''
  createModel.email = ''
  createModel.phone = ''
  createModel.department_id = null
  createModel.role_ids = []
  createModel.temporary_password = ''
  dialogError.value = null
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  const valid = await createFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  dialogError.value = null
  createSubmitting.value = true
  try {
    const payload: CreateUserRequest = {
      username: createModel.username,
      display_name: createModel.display_name,
      email: createModel.email.trim() === '' ? null : createModel.email.trim(),
      phone: createModel.phone.trim() === '' ? null : createModel.phone.trim(),
      department_id: createModel.department_id,
      role_ids: [...createModel.role_ids],
      temporary_password:
        createModel.temporary_password.trim() === '' ? null : createModel.temporary_password,
    }
    await createUser(payload)
    notify.success('用户已创建')
    createVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    createSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 编辑用户
// ---------------------------------------------------------------------------

interface EditUserFormModel {
  display_name: string
  email: string
  phone: string
  status: string
  department_id: string | null
}

const editModel = reactive<EditUserFormModel>({
  display_name: '',
  email: '',
  phone: '',
  status: 'ACTIVE',
  department_id: null,
})

const editRules: FormRules = {
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
}

const editVisible = ref(false)
const editSubmitting = ref(false)
const editFormRef = ref<InstanceType<typeof BaseForm>>()

function openEdit(row: Record<string, unknown>): void {
  const user = toAdminUser(row)
  activeUser.value = user
  editModel.display_name = user.display_name
  editModel.email = user.email ?? ''
  editModel.phone = user.phone ?? ''
  editModel.status = user.status
  editModel.department_id = user.department_id ?? null
  dialogError.value = null
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  const user = activeUser.value
  if (user === null) {
    return
  }
  const valid = await editFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  dialogError.value = null
  editSubmitting.value = true
  try {
    const payload: UpdateUserRequest = {
      display_name: editModel.display_name,
      email: editModel.email.trim() === '' ? null : editModel.email.trim(),
      phone: editModel.phone.trim() === '' ? null : editModel.phone.trim(),
      status: editModel.status,
      department_id: editModel.department_id,
    }
    await updateUser(user.id, payload)
    notify.success('用户已更新')
    editVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    editSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 分配角色
// ---------------------------------------------------------------------------

const rolesVisible = ref(false)
const rolesSubmitting = ref(false)
const assignRoleIds = ref<string[]>([])

async function openAssignRoles(row: Record<string, unknown>): Promise<void> {
  const user = toAdminUser(row)
  activeUser.value = user
  assignRoleIds.value = []
  dialogError.value = null
  rolesVisible.value = true
  if (rolesPage.value === null) {
    await reloadRoles()
  }
  try {
    const briefs = await getUserRoles(user.id)
    assignRoleIds.value = briefs.map((brief) => brief.id)
  } catch (caught) {
    dialogError.value = renderError(caught)
  }
}

async function submitRoles(): Promise<void> {
  const user = activeUser.value
  if (user === null) {
    return
  }
  dialogError.value = null
  rolesSubmitting.value = true
  try {
    await assignUserRoles(user.id, { role_ids: [...assignRoleIds.value] })
    notify.success('用户角色已更新')
    rolesVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    rolesSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 移动部门
// ---------------------------------------------------------------------------

const moveVisible = ref(false)
const moveSubmitting = ref(false)
const moveDepartmentId = ref<string | null>(null)

function openMove(row: Record<string, unknown>): void {
  const user = toAdminUser(row)
  activeUser.value = user
  moveDepartmentId.value = user.department_id ?? null
  dialogError.value = null
  moveVisible.value = true
}

async function submitMove(): Promise<void> {
  const user = activeUser.value
  if (user === null) {
    return
  }
  dialogError.value = null
  moveSubmitting.value = true
  try {
    await moveUserDepartment(user.id, { department_id: moveDepartmentId.value })
    notify.success('用户部门已更新')
    moveVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    moveSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 重置密码
// ---------------------------------------------------------------------------

const resetVisible = ref(false)
const resetSubmitting = ref(false)
const resetReason = ref('')
const resetResult = ref<ResetPasswordResult | null>(null)
const resetResultVisible = ref(false)

function openReset(row: Record<string, unknown>): void {
  const user = toAdminUser(row)
  activeUser.value = user
  resetReason.value = ''
  dialogError.value = null
  resetVisible.value = true
}

async function submitReset(): Promise<void> {
  const user = activeUser.value
  if (user === null) {
    return
  }
  dialogError.value = null
  resetSubmitting.value = true
  try {
    const reason = resetReason.value.trim()
    const result = await resetUserPassword(user.id, {
      user_id: user.id,
      reason: reason === '' ? null : reason,
    })
    resetVisible.value = false
    resetResult.value = result
    resetResultVisible.value = true
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    resetSubmitting.value = false
  }
}

watch(resetResultVisible, (visible) => {
  if (!visible) {
    resetResult.value = null
  }
})

function copyTemporaryPassword(): void {
  const password = resetResult.value?.temporary_password
  if (password === undefined) {
    return
  }
  void clipboard.copy(password, '临时密码已复制')
}

// ---------------------------------------------------------------------------
// 启用 / 禁用 / 删除
// ---------------------------------------------------------------------------

async function onToggleStatus(row: Record<string, unknown>): Promise<void> {
  const user = toAdminUser(row)
  const isActive = user.status === 'ACTIVE'
  if (isActive && isSelfSuperAdmin(row)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  if (isActive) {
    const confirmed = await notify.confirm({
      title: '禁用用户',
      message: `确定要禁用「${user.display_name}」吗？该账号将无法登录。`,
      danger: true,
    })
    if (!confirmed) {
      return
    }
  }
  try {
    if (isActive) {
      await disableUser(user.id)
    } else {
      await enableUser(user.id)
    }
    notify.success(isActive ? '用户已禁用' : '用户已启用')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  if (isSelfSuperAdmin(row)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  const user = toAdminUser(row)
  const confirmed = await notify.confirm({
    title: '删除用户',
    message: `确定要删除「${user.display_name}」吗？该操作为逻辑删除且不可撤销。`,
    danger: true,
    requireTypedText: user.username,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteUser(user.id)
    notify.success('用户已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 详情抽屉
// ---------------------------------------------------------------------------

interface UserDetail {
  user: AdminUser | null
  roles: { id: string; role_code: string; role_name: string; data_scope: string }[]
}

const detailVisible = ref(false)
const detailUserId = ref<string | null>(null)

const {
  data: detail,
  loading: detailLoading,
  failed: detailFailed,
  error: detailError,
  reload: reloadDetail,
} = useAsyncData<UserDetail>(
  async () => {
    const id = detailUserId.value
    if (id === null) {
      return { user: null, roles: [] }
    }
    const [user, roles] = await Promise.all([getUser(id), getUserRoles(id)])
    return { user, roles }
  },
  { immediate: false },
)

const {
  data: sessions,
  loading: sessionsLoading,
  failed: sessionsFailed,
  error: sessionsError,
  reload: reloadSessions,
} = useAsyncData(
  () =>
    detailUserId.value === null ? Promise.resolve([]) : getUserSessions(detailUserId.value),
  { immediate: false },
)

const detailUser = computed(() => detail.value?.user ?? null)
const detailRoles = computed(() => detail.value?.roles ?? [])
const sessionRows = computed(() => asRows(sessions.value ?? []))

function openDetail(row: Record<string, unknown>): void {
  detailUserId.value = String(row.id)
  detailVisible.value = true
  void reloadDetail()
  void reloadSessions()
}

function reloadDetailAll(): void {
  void reloadDetail()
  void reloadSessions()
}

watch(detailVisible, (visible) => {
  if (!visible) {
    detailUserId.value = null
  }
})
</script>

<template>
  <div class="user-page">
    <PageHeader title="用户管理" description="管理管理员账号、角色、所属部门与会话。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-permission="PERMISSION.userCreate" type="primary" @click="openCreate">
          新建用户
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="user-page__filters">
      <ElRow :gutter="12">
        <ElCol :xs="24" :sm="8" :md="6">
          <ElInput
            v-model="filters.keyword"
            placeholder="用户名 / 显示名称"
            clearable
            @keyup.enter="search"
          />
        </ElCol>
        <ElCol :xs="24" :sm="8" :md="6">
          <ElSelect
            v-model="filters.department_id"
            placeholder="所属部门"
            clearable
            style="width: 100%"
          >
            <ElOption
              v-for="item in departmentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :sm="8" :md="6">
          <ElSelect v-model="filters.status" placeholder="状态" clearable style="width: 100%">
            <ElOption
              v-for="item in USER_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :md="6">
          <ElSpace>
            <ElButton type="primary" @click="search">查询</ElButton>
            <ElButton @click="resetFilters">重置</ElButton>
          </ElSpace>
        </ElCol>
      </ElRow>
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
        empty-text="暂无用户"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('username')"
          prop="username"
          label="用户名"
          min-width="140"
        />
        <ElTableColumn
          v-if="!fields.isHidden('display_name')"
          prop="display_name"
          label="显示名称"
          min-width="140"
        />
        <ElTableColumn v-if="!fields.isHidden('department_id')" label="部门" min-width="140">
          <template #default="{ row }">{{ row.department_name ?? '—' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="96">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('is_super_admin')" label="超管" width="88">
          <template #default="{ row }">
            <StatusTag :value="row.is_super_admin" :boolean-labels="['否', '是']" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('last_login_at')" label="上次登录" width="180">
          <template #default="{ row }">{{ formatDateTime(row.last_login_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canManage" label="操作" width="380" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
              <ElButton
                v-permission="PERMISSION.userEdit"
                link
                type="primary"
                @click="openEdit(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-permission="PERMISSION.roleAssign"
                link
                type="primary"
                @click="openAssignRoles(row)"
              >
                分配角色
              </ElButton>
              <ElButton
                v-permission="PERMISSION.userEdit"
                link
                type="primary"
                @click="openMove(row)"
              >
                移动部门
              </ElButton>
              <ElButton
                v-permission="PERMISSION.userResetPassword"
                link
                type="warning"
                @click="openReset(row)"
              >
                重置密码
              </ElButton>
              <ElTooltip
                :content="SELF_ACTION_HINT"
                placement="top"
                :disabled="!isSelfSuperAdmin(row)"
              >
                <span class="user-page__action">
                  <ElButton
                    v-permission="PERMISSION.userEdit"
                    link
                    :type="row.status === 'ACTIVE' ? 'danger' : 'success'"
                    :disabled="row.status === 'ACTIVE' && isSelfSuperAdmin(row)"
                    @click="onToggleStatus(row)"
                  >
                    {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
                  </ElButton>
                </span>
              </ElTooltip>
              <ElTooltip
                :content="SELF_ACTION_HINT"
                placement="top"
                :disabled="!isSelfSuperAdmin(row)"
              >
                <span class="user-page__action">
                  <ElButton
                    v-permission="PERMISSION.userDelete"
                    link
                    type="danger"
                    :disabled="isSelfSuperAdmin(row)"
                    @click="onDelete(row)"
                  >
                    删除
                  </ElButton>
                </span>
              </ElTooltip>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <!-- 新建用户 -->
    <BaseDialog
      v-model="createVisible"
      title="新建用户"
      :confirm-loading="createSubmitting"
      @confirm="submitCreate"
    >
      <BaseForm
        ref="createFormRef"
        :model="createModel"
        :rules="createRules"
        :error-message="toMessages().message"
        :error-trace-id="toMessages().traceId"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('username')" label="用户名" prop="username">
          <ElInput
            v-model="createModel.username"
            :disabled="fields.isReadOnly('username')"
            placeholder="登录账号"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('display_name')" label="显示名称" prop="display_name">
          <ElInput
            v-model="createModel.display_name"
            :disabled="fields.isReadOnly('display_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('email')" label="邮箱">
          <ElInput v-model="createModel.email" :disabled="fields.isReadOnly('email')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('phone')" label="手机号">
          <ElInput v-model="createModel.phone" :disabled="fields.isReadOnly('phone')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('department_id')" label="所属部门">
          <ElSelect
            v-model="createModel.department_id"
            clearable
            :disabled="fields.isReadOnly('department_id')"
            placeholder="请选择部门"
          >
            <ElOption
              v-for="item in departmentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('role_ids')" label="角色">
          <ElSelect
            v-model="createModel.role_ids"
            multiple
            :disabled="fields.isReadOnly('role_ids')"
            placeholder="请选择角色"
          >
            <ElOption
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('temporary_password')" label="初始密码">
          <ElInput
            v-model="createModel.temporary_password"
            :disabled="fields.isReadOnly('temporary_password')"
            placeholder="留空则由系统生成"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <!-- 编辑用户 -->
    <BaseDialog
      v-model="editVisible"
      :title="activeUser ? `编辑用户：${activeUser.username}` : '编辑用户'"
      :confirm-loading="editSubmitting"
      @confirm="submitEdit"
    >
      <BaseForm
        ref="editFormRef"
        :model="editModel"
        :rules="editRules"
        :error-message="toMessages().message"
        :error-trace-id="toMessages().traceId"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('display_name')" label="显示名称" prop="display_name">
          <ElInput
            v-model="editModel.display_name"
            :disabled="fields.isReadOnly('display_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('email')" label="邮箱">
          <ElInput v-model="editModel.email" :disabled="fields.isReadOnly('email')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('phone')" label="手机号">
          <ElInput v-model="editModel.phone" :disabled="fields.isReadOnly('phone')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('status')" label="状态">
          <ElSelect v-model="editModel.status" :disabled="fields.isReadOnly('status')">
            <ElOption
              v-for="item in USER_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('department_id')" label="所属部门">
          <ElSelect
            v-model="editModel.department_id"
            clearable
            :disabled="fields.isReadOnly('department_id')"
            placeholder="请选择部门"
          >
            <ElOption
              v-for="item in departmentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </ElSelect>
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <!-- 分配角色 -->
    <BaseDialog
      v-model="rolesVisible"
      :title="activeUser ? `分配角色：${activeUser.display_name}` : '分配角色'"
      :confirm-loading="rolesSubmitting"
      @confirm="submitRoles"
    >
      <ElAlert
        v-if="dialogError"
        type="error"
        :closable="false"
        show-icon
        title="操作失败"
        :description="dialogError.message"
      />
      <p v-if="dialogError?.traceId" class="user-page__trace">
        Trace ID: {{ dialogError.traceId }}
      </p>
      <ElSelect v-model="assignRoleIds" multiple placeholder="请选择角色" style="width: 100%">
        <ElOption
          v-for="role in roleOptions"
          :key="role.value"
          :label="role.label"
          :value="role.value"
        />
      </ElSelect>
    </BaseDialog>

    <!-- 移动部门 -->
    <BaseDialog
      v-model="moveVisible"
      :title="activeUser ? `移动部门：${activeUser.display_name}` : '移动部门'"
      :confirm-loading="moveSubmitting"
      @confirm="submitMove"
    >
      <ElAlert
        v-if="dialogError"
        type="error"
        :closable="false"
        show-icon
        title="提交失败"
        :description="dialogError.message"
      />
      <p v-if="dialogError?.traceId" class="user-page__trace">
        Trace ID: {{ dialogError.traceId }}
      </p>
      <ElSelect v-model="moveDepartmentId" clearable placeholder="请选择部门" style="width: 100%">
        <ElOption
          v-for="item in departmentOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </ElSelect>
    </BaseDialog>

    <!-- 重置密码 -->
    <BaseDialog
      v-model="resetVisible"
      :title="activeUser ? `重置密码：${activeUser.display_name}` : '重置密码'"
      :confirm-loading="resetSubmitting"
      @confirm="submitReset"
    >
      <ElAlert
        type="warning"
        :closable="false"
        show-icon
        title="重置后需用户使用临时密码登录"
        description="重置成功后临时密码只显示一次，请立即复制并安全地转交给用户。"
      />
      <ElAlert
        v-if="dialogError"
        type="error"
        :closable="false"
        show-icon
        title="重置失败"
        :description="dialogError.message"
        class="user-page__error"
      />
      <p v-if="dialogError?.traceId" class="user-page__trace">
        Trace ID: {{ dialogError.traceId }}
      </p>
      <ElFormItem label="重置原因" label-width="90px">
        <ElInput v-model="resetReason" placeholder="可选，用于审计" />
      </ElFormItem>
    </BaseDialog>

    <!-- 重置结果（仅显示一次） -->
    <BaseDialog v-model="resetResultVisible" title="密码已重置" width="480px" hide-footer>
      <ElAlert
        type="success"
        :closable="false"
        show-icon
        title="请立即复制临时密码"
        description="该临时密码仅显示这一次，关闭后将无法再次查看。"
      />
      <div class="user-page__password">
        <code class="user-page__password-value">{{ resetResult?.temporary_password ?? '—' }}</code>
        <ElButton type="primary" @click="copyTemporaryPassword">复制</ElButton>
      </div>
    </BaseDialog>

    <!-- 用户详情 -->
    <ElDrawer v-model="detailVisible" title="用户详情" size="720px" destroy-on-close>
      <DataStateView
        :loading="detailLoading"
        :failed="detailFailed"
        :error="detailError"
        :empty="detailUser === null"
        empty-text="未找到该用户"
        @retry="reloadDetailAll"
      >
        <ElDescriptions v-if="detailUser" :column="2" border>
          <ElDescriptionsItem v-if="!fields.isHidden('username')" label="用户名">
            {{ detailUser.username }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('display_name')" label="显示名称">
            {{ detailUser.display_name }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('status')" label="状态">
            <StatusTag :value="detailUser.status" />
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('is_super_admin')" label="超级管理员">
            <StatusTag :value="detailUser.is_super_admin" :boolean-labels="['否', '是']" />
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('email')" label="邮箱">
            {{ detailUser.email ?? '—' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('phone')" label="手机号">
            {{ detailUser.phone ?? '—' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem v-if="!fields.isHidden('department_id')" label="部门">
            {{ detailUser.department_name ?? '—' }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="需修改密码">
            <StatusTag :value="detailUser.must_change_password" :boolean-labels="['否', '是']" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="失败登录次数">
            {{ detailUser.failed_login_count }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="锁定至">
            {{ formatDateTime(detailUser.locked_until) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="上次登录">
            {{ formatDateTime(detailUser.last_login_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">
            {{ formatDateTime(detailUser.created_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>

        <div v-if="detailUser" class="user-page__section">
          <h4 class="user-page__section-title">角色</h4>
          <ElSpace v-if="detailRoles.length > 0" wrap>
            <ElTag
              v-for="role in detailRoles"
              :key="role.id"
              type="info"
              size="small"
              disable-transitions
            >
              {{ role.role_name }}（{{ role.role_code }}）
            </ElTag>
          </ElSpace>
          <span v-else>—</span>
        </div>
      </DataStateView>

      <div class="user-page__section">
        <h4 class="user-page__section-title">会话</h4>
        <BaseTable
          :rows="sessionRows"
          :loading="sessionsLoading"
          :failed="sessionsFailed"
          :error="sessionsError"
          :total="sessionRows.length"
          :page="1"
          :page-size="sessionRows.length || 1"
          :paginated="false"
          row-key="session_id"
          empty-text="暂无会话记录"
          @retry="reloadSessions"
        >
          <ElTableColumn label="会话 ID" min-width="180">
            <template #default="{ row }">{{ row.session_id ?? row.id ?? '—' }}</template>
          </ElTableColumn>
          <ElTableColumn label="设备" width="110">
            <template #default="{ row }">{{ row.device_type ?? '—' }}</template>
          </ElTableColumn>
          <ElTableColumn label="IP" width="140">
            <template #default="{ row }">{{ row.ip ?? '—' }}</template>
          </ElTableColumn>
          <ElTableColumn label="状态" width="100">
            <template #default="{ row }">
              <StatusTag :value="row.status" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="登录时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.login_at) }}</template>
          </ElTableColumn>
          <ElTableColumn label="最后活动" width="180">
            <template #default="{ row }">{{ formatDateTime(row.last_active_at) }}</template>
          </ElTableColumn>
        </BaseTable>
      </div>
    </ElDrawer>
  </div>
</template>

<style scoped>
.user-page__filters {
  margin-bottom: 16px;
}

.user-page__action {
  display: inline-flex;
}

.user-page__trace {
  margin: 8px 0 0;
  color: var(--vctn-text-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.user-page__error {
  margin-top: 12px;
}

.user-page__password {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.user-page__password-value {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--vctn-border-subtle);
  border-radius: 4px;
  background-color: var(--vctn-bg-hover);
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 14px;
  word-break: break-all;
}

.user-page__section {
  margin-top: 16px;
}

.user-page__section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 500;
}
</style>
