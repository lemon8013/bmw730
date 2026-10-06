<script setup lang="ts">
/**
 * 任务：任务定义的增删改 + 按业务用户查看任务进度。
 *
 * 平台侧的 `/tasks/me` 按登录的业务用户取数，管理员调用一律 401；任务定义此前
 * 完全没有写接口。现补齐 `/admin/tasks` 与 `/admin/users/{id}/tasks`。
 *
 * 任务是**事件驱动**的：conditions.event_code 决定哪个事件推进进度，
 * target_count 决定何时置为完成。本页只维护定义，进度由后端自动累计。
 */
import { computed, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElProgress,
  ElSelect,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import {
  createTask,
  deleteTask,
  getUserTasks,
  listAdminTasks,
  updateTask,
} from '@/api/growth'
import BizUserPicker from '@/components/growth/BizUserPicker.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type { Task, UserTaskAdmin } from '@/types/growth'
import { renderError } from '@/utils/error'

function failureText(caught: unknown): string {
  return renderError(caught).message
}

const notify = useConfirm()
const fields = useFieldPolicy(PERMISSION.taskConfigView)
const permission = usePermissionStore()

const canEdit = computed(() => permission.has(PERMISSION.taskConfigEdit))

const TASK_STATUS = ['ACTIVE', 'DISABLED'] as const
const STATUS_LABEL: Readonly<Record<string, string>> = {
  ACTIVE: '启用',
  DISABLED: '停用',
}

const TASK_TYPES = ['DAILY', 'WEEKLY', 'ONE_TIME'] as const

const MAX_PAGE_SIZE = 200

// ---------------------------------------------------------------------------
// 任务定义
// ---------------------------------------------------------------------------

const {
  data: tasks,
  loading: tasksLoading,
  failed: tasksFailed,
  error: tasksError,
  reload: reloadTasks,
} = useAsyncData(() => listAdminTasks(true))

const taskRows = computed(
  () => (tasks.value ?? []) as unknown as Record<string, unknown>[],
)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()

interface TaskForm {
  task_code: string
  task_name: string
  task_type: string
  event_code: string
  target_count: number
  reward_points: number
  reward_growth_points: number
  repeatable: boolean
  status: string
}

function emptyForm(): TaskForm {
  return {
    task_code: '',
    task_name: '',
    task_type: 'ONE_TIME',
    event_code: '',
    target_count: 1,
    reward_points: 0,
    reward_growth_points: 0,
    repeatable: false,
    status: 'ACTIVE',
  }
}

const form = reactive<TaskForm>(emptyForm())

const formRules: FormRules<TaskForm> = {
  task_code: [{ required: true, message: '请填写任务编码', trigger: 'blur' }],
  task_name: [{ required: true, message: '请填写任务名称', trigger: 'blur' }],
  event_code: [{ required: true, message: '请填写触发事件编码', trigger: 'blur' }],
  target_count: [{ required: true, message: '请填写目标次数', trigger: 'change' }],
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const task = row as unknown as Task
  const conditions = (task.conditions ?? {}) as Record<string, unknown>
  const reward = (task.reward ?? {}) as Record<string, unknown>
  editingId.value = task.id
  Object.assign(form, {
    task_code: task.task_code,
    task_name: task.task_name,
    task_type: task.task_type,
    event_code: String(conditions.event_code ?? ''),
    target_count: Number(conditions.target_count ?? 1),
    reward_points: Number(reward.points ?? 0),
    reward_growth_points: Number(reward.growth_points ?? 0),
    repeatable: task.repeatable,
    status: task.status,
  })
  dialogVisible.value = true
}

async function submitTask(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    const conditions = { event_code: form.event_code, target_count: form.target_count }
    const reward = { points: form.reward_points, growth_points: form.reward_growth_points }
    if (editingId.value === null) {
      await createTask({
        task_code: form.task_code,
        task_name: form.task_name,
        task_type: form.task_type,
        conditions,
        reward,
        repeatable: form.repeatable,
        status: form.status,
      })
      notify.success('已新增任务')
    } else {
      await updateTask(editingId.value, {
        task_name: form.task_name,
        task_type: form.task_type,
        conditions,
        reward,
        repeatable: form.repeatable,
        status: form.status,
      })
      notify.success('已更新任务')
    }
    dialogVisible.value = false
    await reloadTasks()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    submitting.value = false
  }
}

async function removeTask(row: Record<string, unknown>): Promise<void> {
  const task = row as unknown as Task
  const confirmed = await notify.confirm({
    title: '停用任务',
    message: `停用「${task.task_name}」后它不再累计进度。已有进度记录保留，不会被删除。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteTask(task.id)
    notify.success('已停用任务')
    await reloadTasks()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 用户任务进度
// ---------------------------------------------------------------------------

const selectedUserId = ref('')

const {
  data: userTasks,
  loading: userTasksLoading,
  failed: userTasksFailed,
  error: userTasksError,
  reload: reloadUserTasks,
} = useAsyncData(() => getUserTasks(selectedUserId.value), { immediate: false })

const userTaskRows = computed(
  () => (userTasks.value ?? []) as unknown as Record<string, unknown>[],
)

async function onUserChange(user: { user_id: string } | null): Promise<void> {
  const userId = user?.user_id ?? ''
  selectedUserId.value = userId
  if (!userId) {
    return
  }
  await reloadUserTasks()
}

/** 进度百分比；没有目标次数时按完成与否给 0/100。 */
function progressOf(row: Record<string, unknown>): number {
  const item = row as unknown as UserTaskAdmin
  if (!item.target_count || item.target_count <= 0) {
    return item.status === 'COMPLETED' ? 100 : 0
  }
  return Math.min(100, Math.round((item.current_count / item.target_count) * 100))
}

function rewardText(row: Record<string, unknown>): string {
  const item = row as unknown as UserTaskAdmin
  const reward = (item.reward ?? {}) as Record<string, unknown>
  const points = Number(reward.points ?? 0)
  const growth = Number(reward.growth_points ?? 0)
  if (!points && !growth) {
    return '—'
  }
  return `${points ? `${points} 积分` : ''}${points && growth ? ' · ' : ''}${growth ? `${growth} 成长值` : ''}`
}

function refreshAll(): void {
  void reloadTasks()
  if (selectedUserId.value) {
    void reloadUserTasks()
  }
}
</script>

<template>
  <div class="task-page">
    <PageHeader
      title="任务"
      description="任务定义的维护，以及按业务用户查看的任务进度与领奖状态。"
    >
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="task-page__section">
      <template #header>
        <div class="task-page__header">
          <span>任务定义</span>
          <ElButton v-if="canEdit" type="primary" @click="openCreate">新增任务</ElButton>
        </div>
      </template>
      <BaseTable
        :rows="taskRows"
        :loading="tasksLoading"
        :failed="tasksFailed"
        :error="tasksError"
        :total="0"
        :page="1"
        :page-size="MAX_PAGE_SIZE"
        :paginated="false"
        row-key="task_code"
        empty-text="暂无任务"
        @retry="reloadTasks"
      >
        <ElTableColumn
          v-if="!fields.isHidden('task_code')"
          prop="task_code"
          label="任务编码"
          min-width="200"
        />
        <ElTableColumn
          v-if="!fields.isHidden('task_name')"
          prop="task_name"
          label="任务名称"
          min-width="140"
        />
        <ElTableColumn
          v-if="!fields.isHidden('task_type')"
          prop="task_type"
          label="类型"
          width="110"
        />
        <ElTableColumn label="触发事件" min-width="180">
          <template #default="{ row }">
            {{ (row.conditions ?? {}).event_code ?? '—' }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="目标次数" width="100">
          <template #default="{ row }">{{ (row.conditions ?? {}).target_count ?? 1 }}</template>
        </ElTableColumn>
        <ElTableColumn label="奖励" min-width="160">
          <template #default="{ row }">
            <template v-if="row.reward">
              {{ row.reward.points ?? 0 }} 积分 · {{ row.reward.growth_points ?? 0 }} 成长值
            </template>
            <template v-else>—</template>
          </template>
        </ElTableColumn>
        <ElTableColumn label="可重复" width="90">
          <template #default="{ row }">{{ row.repeatable ? '是' : '否' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openEdit(row)">
              {{ canEdit ? '编辑' : '查看' }}
            </ElButton>
            <ElButton v-if="canEdit" link type="danger" @click="removeTask(row)">停用</ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never" class="task-page__section">
      <template #header>
        <div class="task-page__header">
          <span>用户任务进度</span>
          <BizUserPicker :model-value="selectedUserId" width="320px" @change="onUserChange" />
        </div>
      </template>
      <DataStateView
        :loading="userTasksLoading"
        :failed="userTasksFailed"
        :error="userTasksError"
        :empty="!selectedUserId"
        empty-text="请选择业务用户"
        @retry="reloadUserTasks"
      >
        <BaseTable
          :rows="userTaskRows"
          :loading="false"
          :failed="false"
          :total="0"
          :page="1"
          :page-size="MAX_PAGE_SIZE"
          :paginated="false"
          row-key="id"
          empty-text="该用户暂无任务进度"
          @retry="reloadUserTasks"
        >
          <ElTableColumn prop="task_name" label="任务" min-width="140" />
          <ElTableColumn prop="task_type" label="类型" width="110" />
          <ElTableColumn label="进度" min-width="200">
            <template #default="{ row }">
              <ElProgress
                :percentage="progressOf(row)"
                :stroke-width="10"
                :status="row.status === 'COMPLETED' ? 'success' : undefined"
              />
            </template>
          </ElTableColumn>
          <ElTableColumn label="计数" width="130">
            <template #default="{ row }">
              {{ row.current_count }} / {{ row.target_count ?? 1 }}
            </template>
          </ElTableColumn>
          <ElTableColumn prop="status" label="状态" width="120">
            <template #default="{ row }">
              <StatusTag :value="row.status" />
            </template>
          </ElTableColumn>
          <ElTableColumn label="奖励" min-width="160">
            <template #default="{ row }">{{ rewardText(row) }}</template>
          </ElTableColumn>
          <ElTableColumn label="已领奖" width="100">
            <template #default="{ row }">
              <StatusTag :value="row.reward_claimed" :boolean-labels="['未领', '已领']" />
            </template>
          </ElTableColumn>
          <ElTableColumn prop="completed_at" label="完成时间" min-width="180" />
        </BaseTable>
      </DataStateView>
    </ElCard>

    <ElDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增任务' : '编辑任务'"
      width="520px"
    >
      <ElForm ref="formRef" :model="form" :rules="formRules" label-width="120px">
        <ElFormItem label="任务编码" prop="task_code">
          <ElInput v-model="form.task_code" :disabled="editingId !== null" placeholder="TASK_XXX" />
        </ElFormItem>
        <ElFormItem label="任务名称" prop="task_name">
          <ElInput v-model="form.task_name" />
        </ElFormItem>
        <ElFormItem label="任务类型">
          <ElSelect v-model="form.task_type">
            <ElOption v-for="value in TASK_TYPES" :key="value" :label="value" :value="value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="触发事件" prop="event_code">
          <ElInput v-model="form.event_code" placeholder="TOOL_EXECUTION_SUCCESS" />
        </ElFormItem>
        <ElFormItem label="目标次数" prop="target_count">
          <ElInputNumber v-model="form.target_count" :min="1" />
        </ElFormItem>
        <ElFormItem label="奖励积分">
          <ElInputNumber v-model="form.reward_points" :min="0" />
        </ElFormItem>
        <ElFormItem label="奖励成长值">
          <ElInputNumber v-model="form.reward_growth_points" :min="0" />
        </ElFormItem>
        <ElFormItem label="可重复完成">
          <ElSwitch v-model="form.repeatable" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="form.status">
            <ElOption
              v-for="value in TASK_STATUS"
              :key="value"
              :label="STATUS_LABEL[value] ?? value"
              :value="value"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitTask">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.task-page__section {
  margin-top: 16px;
}

.task-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
