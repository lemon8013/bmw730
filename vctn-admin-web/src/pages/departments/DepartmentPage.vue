<script setup lang="ts">
/** 部门管理：左侧部门树，右侧部门详情与部门用户。 */
import { computed, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElRow,
  ElSelect,
  ElSpace,
  ElTableColumn,
  ElTag,
  ElTree,
  type FormRules,
  type TreeData,
} from 'element-plus'

import {
  createDepartment,
  deleteDepartment,
  fetchDepartmentTree,
  getDepartment,
  updateDepartment,
} from '@/api/departments'
import { listDepartmentUsers } from '@/api/users'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import { ACTIVE_STATUS, STATUS_LABEL } from '@/types/enums'
import type {
  CreateDepartmentRequest,
  DepartmentTreeNode,
  UpdateDepartmentRequest,
} from '@/types/system'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.departmentView)

/** 部门用户列表来自用户模块，需同时具备用户查看权限。 */
const canViewUsers = computed(() => permission.has(PERMISSION.userView))

const treeProps = { label: 'department_name', children: 'children' }

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
// 部门树
// ---------------------------------------------------------------------------

const {
  data: treeNodes,
  loading: treeLoading,
  failed: treeFailed,
  error: treeError,
  reload: reloadTree,
} = useAsyncData(() => fetchDepartmentTree())

const treeData = computed(() => (treeNodes.value ?? []) as unknown as TreeData)

const selectedId = ref<string | null>(null)

/** 父级下拉选项：把部门树按层级展开。 */
const parentOptions = computed(() => {
  const options: { value: string; label: string }[] = []
  const walk = (nodes: DepartmentTreeNode[], depth: number): void => {
    for (const node of nodes) {
      options.push({ value: node.id, label: `${'　'.repeat(depth)}${node.department_name}` })
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1)
      }
    }
  }
  walk(treeNodes.value ?? [], 0)
  return options
})

function onNodeClick(node: Record<string, unknown>): void {
  selectedId.value = String(node.id)
  void reloadDetail()
  void reloadUsers()
}

// ---------------------------------------------------------------------------
// 部门详情与用户
// ---------------------------------------------------------------------------

const {
  data: detail,
  loading: detailLoading,
  failed: detailFailed,
  error: detailError,
  reload: reloadDetail,
} = useAsyncData(
  () => (selectedId.value === null ? Promise.resolve(null) : getDepartment(selectedId.value)),
  { immediate: false },
)

const {
  data: userData,
  loading: userLoading,
  failed: userFailed,
  error: userError,
  reload: reloadUsers,
} = useAsyncData(
  () =>
    selectedId.value === null
      ? Promise.resolve([])
      : listDepartmentUsers(selectedId.value),
  { immediate: false },
)

const userRows = computed(() => asRows(userData.value ?? []))

function refreshAll(): void {
  void reloadTree()
  if (selectedId.value !== null) {
    void reloadDetail()
    void reloadUsers()
  }
}

// ---------------------------------------------------------------------------
// 新建 / 编辑
// ---------------------------------------------------------------------------

interface DepartmentFormModel {
  department_code: string
  department_name: string
  parent_id: string | null
  sort_order: number
  status: string
  description: string
}

const formModel = reactive<DepartmentFormModel>({
  department_code: '',
  department_name: '',
  parent_id: null,
  sort_order: 0,
  status: 'ACTIVE',
  description: '',
})

const rules: FormRules = {
  department_code: [{ required: true, message: '请输入部门编码', trigger: 'blur' }],
  department_name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
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

function openCreate(parentId: string | null): void {
  editingId.value = null
  formModel.department_code = ''
  formModel.department_name = ''
  formModel.parent_id = parentId
  formModel.sort_order = 0
  formModel.status = 'ACTIVE'
  formModel.description = ''
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(): void {
  const department = detail.value
  if (department === null) {
    return
  }
  editingId.value = department.id
  formModel.department_code = department.department_code
  formModel.department_name = department.department_name
  formModel.parent_id = department.parent_id ?? null
  formModel.sort_order = department.sort_order
  formModel.status = department.status
  formModel.description = department.description ?? ''
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
      const payload: CreateDepartmentRequest = {
        department_code: formModel.department_code,
        department_name: formModel.department_name,
        parent_id: formModel.parent_id,
        sort_order: formModel.sort_order,
        description: description === '' ? null : description,
      }
      const created = await createDepartment(payload)
      notify.success('部门已创建')
      selectedId.value = created.id
    } else {
      const payload: UpdateDepartmentRequest = {
        department_name: formModel.department_name,
        parent_id: formModel.parent_id,
        sort_order: formModel.sort_order,
        status: formModel.status,
        description: description === '' ? null : description,
      }
      await updateDepartment(editingId.value, payload)
      notify.success('部门已更新')
    }
    dialogVisible.value = false
    await reloadTree()
    if (selectedId.value !== null) {
      await reloadDetail()
      await reloadUsers()
    }
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

async function onToggleStatus(): Promise<void> {
  const department = detail.value
  if (department === null) {
    return
  }
  const nextStatus = department.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'
  if (nextStatus === 'DISABLED') {
    const confirmed = await notify.confirm({
      title: '禁用部门',
      message: `确定要禁用「${department.department_name}」吗？禁用后其下用户的数据范围可能受到影响。`,
      danger: true,
    })
    if (!confirmed) {
      return
    }
  }
  try {
    await updateDepartment(department.id, { status: nextStatus })
    notify.success(nextStatus === 'ACTIVE' ? '部门已启用' : '部门已禁用')
    await reloadTree()
    await reloadDetail()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDelete(): Promise<void> {
  const department = detail.value
  if (department === null) {
    return
  }
  const confirmed = await notify.confirm({
    title: '删除部门',
    message: `确定要删除「${department.department_name}」吗？该操作不可撤销。`,
    danger: true,
    requireTypedText: department.department_code,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteDepartment(department.id)
    notify.success('部门已删除')
    selectedId.value = null
    detail.value = null
    await reloadTree()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="department-page">
    <PageHeader title="部门管理" description="维护组织结构树，查看部门下的用户并管理部门状态。">
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.departmentCreate"
          type="primary"
          @click="openCreate(null)"
        >
          新建部门
        </ElButton>
      </template>
    </PageHeader>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="8">
        <ElCard shadow="never">
          <template #header>部门树</template>
          <DataStateView
            :loading="treeLoading"
            :failed="treeFailed"
            :error="treeError"
            :empty="treeData.length === 0"
            empty-text="暂无部门数据"
            @retry="reloadTree"
          >
            <ElTree
              :data="treeData"
              :props="treeProps"
              node-key="id"
              default-expand-all
              highlight-current
              @node-click="onNodeClick"
            >
              <template #default="{ data }">
                <span class="department-page__node">
                  <span>{{ data.department_name }}</span>
                  <ElTag v-if="data.user_count" size="small" type="info" disable-transitions>
                    {{ data.user_count }}
                  </ElTag>
                  <ElTag v-if="data.status === 'DISABLED'" size="small" type="info" disable-transitions>
                    禁用
                  </ElTag>
                </span>
              </template>
            </ElTree>
          </DataStateView>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="16">
        <ElCard shadow="never">
          <template #header>
            <div class="department-page__detail-header">
              <span>部门详情</span>
              <ElSpace v-if="detail">
                <ElButton
                  v-permission="PERMISSION.departmentCreate"
                  size="small"
                  @click="openCreate(detail.id)"
                >
                  新建子部门
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.departmentEdit"
                  type="primary"
                  size="small"
                  @click="openEdit"
                >
                  编辑
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.departmentEdit"
                  size="small"
                  :type="detail.status === 'ACTIVE' ? 'danger' : 'success'"
                  @click="onToggleStatus"
                >
                  {{ detail.status === 'ACTIVE' ? '禁用' : '启用' }}
                </ElButton>
                <ElButton
                  v-permission="PERMISSION.departmentDelete"
                  type="danger"
                  size="small"
                  @click="onDelete"
                >
                  删除
                </ElButton>
              </ElSpace>
            </div>
          </template>

          <DataStateView
            :loading="detailLoading"
            :failed="detailFailed"
            :error="detailError"
            :empty="detail === null"
            empty-text="请选择左侧的部门"
            @retry="reloadDetail"
          >
            <ElDescriptions v-if="detail" :column="2" border>
              <ElDescriptionsItem
                v-if="!fields.isHidden('department_code')"
                label="部门编码"
              >
                {{ detail.department_code }}
              </ElDescriptionsItem>
              <ElDescriptionsItem
                v-if="!fields.isHidden('department_name')"
                label="部门名称"
              >
                {{ detail.department_name }}
              </ElDescriptionsItem>
              <ElDescriptionsItem v-if="!fields.isHidden('status')" label="状态">
                <StatusTag :value="detail.status" />
              </ElDescriptionsItem>
              <ElDescriptionsItem v-if="!fields.isHidden('sort_order')" label="排序">
                {{ detail.sort_order }}
              </ElDescriptionsItem>
              <ElDescriptionsItem v-if="!fields.isHidden('user_count')" label="用户数">
                {{ detail.user_count ?? 0 }}
              </ElDescriptionsItem>
              <ElDescriptionsItem label="创建时间">
                {{ formatDateTime(detail.created_at) }}
              </ElDescriptionsItem>
              <ElDescriptionsItem
                v-if="!fields.isHidden('description')"
                label="描述"
                :span="2"
              >
                {{ detail.description ?? '—' }}
              </ElDescriptionsItem>
            </ElDescriptions>
          </DataStateView>

          <div v-if="selectedId !== null && canViewUsers" class="department-page__users">
            <h4 class="department-page__users-title">部门用户</h4>
            <BaseTable
              :rows="userRows"
              :loading="userLoading"
              :failed="userFailed"
              :error="userError"
              :total="userRows.length"
              :page="1"
              :page-size="userRows.length || 1"
              :paginated="false"
              empty-text="该部门暂无用户"
              @retry="reloadUsers"
            >
              <ElTableColumn prop="username" label="用户名" min-width="140" />
              <ElTableColumn prop="display_name" label="显示名称" min-width="140" />
              <ElTableColumn prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <StatusTag :value="row.status" />
                </template>
              </ElTableColumn>
            </BaseTable>
          </div>
        </ElCard>
      </ElCol>
    </ElRow>

    <BaseDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建部门' : '编辑部门'"
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
        <ElFormItem
          v-if="!fields.isHidden('department_code')"
          label="部门编码"
          prop="department_code"
        >
          <ElInput
            v-model="formModel.department_code"
            :disabled="editingId !== null || fields.isReadOnly('department_code')"
            placeholder="例如 TECH"
          />
        </ElFormItem>
        <ElFormItem
          v-if="!fields.isHidden('department_name')"
          label="部门名称"
          prop="department_name"
        >
          <ElInput
            v-model="formModel.department_name"
            :disabled="fields.isReadOnly('department_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('parent_id')" label="上级部门">
          <ElSelect
            v-model="formModel.parent_id"
            clearable
            :disabled="fields.isReadOnly('parent_id')"
            placeholder="不选表示顶级部门"
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
            v-model="formModel.description"
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
.department-page__node {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

.department-page__detail-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.department-page__users {
  margin-top: 16px;
}

.department-page__users-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 500;
}
</style>
