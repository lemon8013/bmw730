<script setup lang="ts">
/** 会话管理：先选择用户，再查看该用户的会话明细，并支持强制下线。 */
import { computed, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElSpace,
  ElTableColumn,
  ElTooltip,
} from 'element-plus'

import { forceLogout, getUserSessions, listUsers } from '@/api/users'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import type { AdminUser, UserSessionRow } from '@/types/system'
import { renderError } from '@/utils/error'
import { formatDateTime, sameId } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
const auth = useAuthStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.sessionView)

/** 是否具备会话强制下线权限。 */
const canRevoke = computed(() => permission.has(PERMISSION.sessionRevoke))

/** 禁止对当前登录的超级管理员本人执行的动作提示。 */
const SELF_ACTION_HINT = '不能对当前登录的超级管理员执行该操作'

/** 目标用户是否为当前登录的超级管理员本人。 */
function isSelfSuperAdmin(user: AdminUser | null): boolean {
  const self = auth.user
  if (user === null || self === null || !auth.isSuperAdmin || !user.is_super_admin) {
    return false
  }
  return sameId(user.id, self.id) || user.username === self.username
}

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

/** 会话行的标识：后端可能返回 `session_id` 或 `id`。 */
function sessionId(row: Record<string, unknown>): string {
  const value = row.session_id ?? row.id
  return value === null || value === undefined ? '—' : String(value)
}

// ---------------------------------------------------------------------------
// 用户选择
// ---------------------------------------------------------------------------

const keyword = ref('')
const selectedUser = ref<AdminUser | null>(null)

const {
  data: userData,
  loading: usersLoading,
  failed: usersFailed,
  error: usersError,
  reload: reloadUsers,
} = useAsyncData(() =>
  listUsers({
    keyword: keyword.value.trim() === '' ? undefined : keyword.value.trim(),
    page: 1,
    page_size: 20,
  }),
)

const userRows = computed(() => asRows(userData.value?.items ?? []))

function searchUsers(): void {
  void reloadUsers()
}

function resetUsers(): void {
  keyword.value = ''
  selectedUser.value = null
  void reloadUsers()
}

function selectUser(row: Record<string, unknown>): void {
  selectedUser.value = row as unknown as AdminUser
  void reloadSessions()
}

// ---------------------------------------------------------------------------
// 会话明细
// ---------------------------------------------------------------------------

const {
  data: sessionData,
  loading: sessionsLoading,
  failed: sessionsFailed,
  error: sessionsError,
  reload: reloadSessions,
} = useAsyncData<UserSessionRow[]>(
  () =>
    selectedUser.value === null
      ? Promise.resolve([])
      : getUserSessions(selectedUser.value.id),
  { immediate: false },
)

const sessionRows = computed(() => asRows(sessionData.value ?? []))

// ---------------------------------------------------------------------------
// 强制下线
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const reason = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openForceLogout(): void {
  if (selectedUser.value === null) {
    return
  }
  if (isSelfSuperAdmin(selectedUser.value)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  reason.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

async function submitForceLogout(): Promise<void> {
  const user = selectedUser.value
  if (user === null) {
    return
  }
  if (isSelfSuperAdmin(user)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  const confirmed = await notify.confirm({
    title: '强制下线',
    message: `确定要强制「${user.username}」下线吗？该用户的所有会话将立即失效。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    const result = await forceLogout(user.id, {
      reason: reason.value.trim() === '' ? null : reason.value.trim(),
    })
    notify.success(`已强制下线，撤销会话 ${result.revoked_sessions} 个`)
    dialogVisible.value = false
    await reloadSessions()
  } catch (caught) {
    const rendered = renderError(caught)
    submitError.value = rendered.message
    submitTrace.value = rendered.traceId ?? null
    notify.failure(failureText(caught))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="session-page">
    <PageHeader title="会话管理" description="按用户查看会话明细，并支持对目标用户强制下线。">
      <template #actions>
        <ElButton @click="reloadUsers">刷新用户</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="session-page__picker">
      <template #header>选择用户</template>
      <ElSpace wrap class="session-page__search">
        <ElInput
          v-model="keyword"
          placeholder="按用户名或显示名称搜索"
          clearable
          style="width: 260px"
        />
        <ElButton type="primary" @click="searchUsers">查询</ElButton>
        <ElButton @click="resetUsers">重置</ElButton>
      </ElSpace>

      <BaseTable
        :rows="userRows"
        :loading="usersLoading"
        :failed="usersFailed"
        :error="usersError"
        :total="userRows.length"
        :page="1"
        :page-size="userRows.length || 1"
        :paginated="false"
        empty-text="没有匹配的用户"
        @retry="reloadUsers"
      >
        <ElTableColumn prop="username" label="用户名" min-width="140" />
        <ElTableColumn prop="display_name" label="显示名称" min-width="140" />
        <ElTableColumn label="状态" width="110">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="selectUser(row)">查看会话</ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never">
      <template #header>
        <div class="session-page__header">
          <span>
            会话明细
            <template v-if="selectedUser">
              · {{ selectedUser.display_name }}（{{ selectedUser.username }}）
            </template>
          </span>
          <ElTooltip
            v-if="selectedUser && canRevoke"
            :content="SELF_ACTION_HINT"
            placement="top"
            :disabled="!isSelfSuperAdmin(selectedUser)"
          >
            <span class="session-page__action">
              <ElButton
                v-permission="PERMISSION.sessionRevoke"
                type="danger"
                size="small"
                :disabled="isSelfSuperAdmin(selectedUser)"
                @click="openForceLogout"
              >
                强制下线
              </ElButton>
            </span>
          </ElTooltip>
        </div>
      </template>

      <ElAlert
        v-if="selectedUser === null"
        type="info"
        :closable="false"
        show-icon
        title="请先在上方选择用户"
      />

      <BaseTable
        v-else
        :rows="sessionRows"
        :loading="sessionsLoading"
        :failed="sessionsFailed"
        :error="sessionsError"
        :total="sessionRows.length"
        :page="1"
        :page-size="sessionRows.length || 1"
        :paginated="false"
        empty-text="该用户没有会话记录"
        @retry="reloadSessions"
      >
        <ElTableColumn
          v-if="!fields.isHidden('session_id')"
          label="会话 ID"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">{{ sessionId(row) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" label="状态" width="110">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('ip')" prop="ip" label="IP" width="140" />
        <ElTableColumn
          v-if="!fields.isHidden('device_type')"
          prop="device_type"
          label="设备类型"
          width="120"
        />
        <ElTableColumn
          v-if="!fields.isHidden('user_agent')"
          prop="user_agent"
          label="User Agent"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('login_at')" label="登录时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.login_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="最后活跃" width="180">
          <template #default="{ row }">{{ formatDateTime(row.last_active_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="过期时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="撤销时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.revoked_at) }}</template>
        </ElTableColumn>
        <ElTableColumn
          prop="revoke_reason"
          label="撤销原因"
          min-width="160"
          show-overflow-tooltip
        />
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      title="强制下线"
      :confirm-loading="submitting"
      confirm-text="确认下线"
      width="520px"
      @confirm="submitForceLogout"
    >
      <BaseForm
        :model="{ reason }"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem label="用户">
          <span>{{ selectedUser?.username ?? '—' }}</span>
        </ElFormItem>
        <ElFormItem label="下线原因">
          <ElInput
            v-model="reason"
            type="textarea"
            :rows="2"
            placeholder="可选，便于审计追溯"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.session-page__picker {
  margin-bottom: 16px;
}

.session-page__search {
  margin-bottom: 12px;
}

.session-page__header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.session-page__action {
  display: inline-flex;
}
</style>
