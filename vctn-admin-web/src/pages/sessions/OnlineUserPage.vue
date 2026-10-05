<script setup lang="ts">
/** 在线用户：查看当前在线会话，并支持按用户名本地筛选与强制下线。 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElSpace,
  ElTableColumn,
  ElTooltip,
} from 'element-plus'

import { forceLogout, listOnlineUsers } from '@/api/users'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import type { OnlineUser } from '@/types/system'
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

/** 给定身份是否为当前登录的超级管理员本人。 */
function isSelfIdentity(userId: string, username: string): boolean {
  const self = auth.user
  if (self === null || !auth.isSuperAdmin) {
    return false
  }
  return sameId(userId, self.id) || username === self.username
}

/** 目标行是否为当前登录的超级管理员本人。 */
function isSelfSuperAdmin(row: Record<string, unknown>): boolean {
  return isSelfIdentity(String(row.user_id), String(row.username))
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

// ---------------------------------------------------------------------------
// 在线会话
// ---------------------------------------------------------------------------

/** 用户名筛选：仅在已加载的行上做本地 computed，不在键盘事件中重新请求。 */
const keyword = ref('')

const { data, loading, failed, error, reload } = useAsyncData(() => listOnlineUsers())

const allRows = computed(() => asRows(data.value ?? []))

const rows = computed(() => {
  const needle = keyword.value.trim().toLowerCase()
  if (needle === '') {
    return allRows.value
  }
  return allRows.value.filter((row) =>
    String(row.username ?? '')
      .toLowerCase()
      .includes(needle),
  )
})

function resetFilters(): void {
  keyword.value = ''
  void reload()
}

// ---------------------------------------------------------------------------
// 强制下线
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const target = ref<OnlineUser | null>(null)
const reason = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openForceLogout(row: Record<string, unknown>): void {
  if (isSelfSuperAdmin(row)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  target.value = row as unknown as OnlineUser
  reason.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

async function submitForceLogout(): Promise<void> {
  const user = target.value
  if (user === null) {
    return
  }
  if (isSelfIdentity(user.user_id, user.username)) {
    notify.warning(SELF_ACTION_HINT)
    return
  }
  const device = user.device_type ?? '未知设备'
  const ip = user.ip ?? '未知 IP'
  const confirmed = await notify.confirm({
    title: '强制下线',
    message: `确定要强制「${user.username}」下线吗？设备：${device}，IP：${ip}。该用户的所有会话将立即失效。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    const result = await forceLogout(user.user_id, {
      reason: reason.value.trim() === '' ? null : reason.value.trim(),
    })
    notify.success(`已强制下线，撤销会话 ${result.revoked_sessions} 个`)
    dialogVisible.value = false
    await reload()
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
  <div class="online-user-page">
    <PageHeader
      title="在线用户"
      description="查看当前在线会话；筛选在已加载数据上本地完成，不触发额外请求。"
    >
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="online-user-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="keyword"
          placeholder="按用户名筛选"
          clearable
          style="width: 240px"
        />
        <ElButton @click="resetFilters">重置</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="rows.length"
        :page="1"
        :page-size="rows.length || 1"
        :paginated="false"
        row-key="session_id"
        empty-text="当前没有在线用户"
        @retry="reload"
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
        <ElTableColumn
          v-if="!fields.isHidden('department_id')"
          prop="department_id"
          label="部门"
          min-width="120"
        />
        <ElTableColumn
          v-if="!fields.isHidden('session_id')"
          prop="session_id"
          label="会话 ID"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('ip')" prop="ip" label="IP" width="140" />
        <ElTableColumn
          v-if="!fields.isHidden('device_type')"
          prop="device_type"
          label="设备类型"
          width="130"
        />
        <ElTableColumn
          v-if="!fields.isHidden('login_at')"
          label="登录时间"
          width="180"
        >
          <template #default="{ row }">{{ formatDateTime(row.login_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="最后活跃" width="180">
          <template #default="{ row }">{{ formatDateTime(row.last_active_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canRevoke" label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <ElTooltip
              :content="SELF_ACTION_HINT"
              placement="top"
              :disabled="!isSelfSuperAdmin(row)"
            >
              <span class="online-user-page__action">
                <ElButton
                  v-permission="PERMISSION.sessionRevoke"
                  link
                  type="danger"
                  :disabled="isSelfSuperAdmin(row)"
                  @click="openForceLogout(row)"
                >
                  强制下线
                </ElButton>
              </span>
            </ElTooltip>
          </template>
        </ElTableColumn>
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
          <span>{{ target?.username ?? '—' }}</span>
        </ElFormItem>
        <ElFormItem label="设备">
          <span>{{ target?.device_type ?? '—' }}</span>
        </ElFormItem>
        <ElFormItem label="IP">
          <span>{{ target?.ip ?? '—' }}</span>
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
.online-user-page__filters {
  margin-bottom: 16px;
}

.online-user-page__action {
  display: inline-flex;
}
</style>
