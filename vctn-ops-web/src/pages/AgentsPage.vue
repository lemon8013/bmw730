<script setup lang="ts">
/**
 * Collection agents.
 *
 * Registration returns the plain token exactly once — the backend stores only a
 * hash — so the response is echoed in a dialog the operator must dismiss, with
 * an explicit warning and a copy button. It is never listed, never logged and
 * never recoverable afterwards.
 */
import { computed, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import {
  disableAgent,
  enableAgent,
  listAgents,
  listHeartbeats,
  registerAgent,
} from '@/api/ops/agents'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { AGENT_STATUS } from '@/types/enums'
import type { Agent } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.agentManage))

const filters = ref({ keyword: '', status: '', enabled: undefined as boolean | undefined })

const list = usePagedList<Agent>((page, pageSize) =>
  listAgents(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    status: filters.value.status === '' ? undefined : filters.value.status,
    enabled: filters.value.enabled,
  }),
)

void list.reload()

/* ---------- registration ---------- */

const registerVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = ref({ agent_code: '', agent_name: '', host_id: '', version: '' })
const rules: FormRules<typeof form.value> = {
  agent_code: [{ required: true, message: '请输入 Agent 编码', trigger: 'blur' }],
  agent_name: [{ required: true, message: '请输入 Agent 名称', trigger: 'blur' }],
}

/** The token returned by the last registration; shown until the dialog closes. */
const issuedToken = ref<string | null>(null)

function openRegister(): void {
  issuedToken.value = null
  form.value = { agent_code: '', agent_name: '', host_id: '', version: '' }
  registerVisible.value = true
}

async function submitRegister(): Promise<void> {
  const instance = formRef.value
  if (instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    const result = await registerAgent({
      agent_code: form.value.agent_code.trim(),
      agent_name: form.value.agent_name.trim(),
      host_id: form.value.host_id.trim() === '' ? null : form.value.host_id.trim(),
      version: form.value.version.trim() === '' ? null : form.value.version.trim(),
    })
    // The only moment the token exists on the client: show it immediately.
    issuedToken.value = result.token
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function copyToken(): Promise<void> {
  if (issuedToken.value === null) {
    return
  }
  try {
    await navigator.clipboard.writeText(issuedToken.value)
    ElMessage.success('Token 已复制')
  } catch {
    ElMessage.warning('浏览器拒绝了剪贴板访问，请手动复制')
  }
}

function closeRegister(): void {
  registerVisible.value = false
  issuedToken.value = null
}

/* ---------- enable / disable ---------- */

/** Element Plus hands rows back as a loose record; narrow it for the handler. */
function asAgent(row: unknown): Agent {
  return row as Agent
}

async function toggle(row: Agent, enabled: boolean): Promise<void> {
  const confirmed = await confirmAction({
    title: enabled ? '启用 Agent' : '停用 Agent',
    message: enabled
      ? `确定启用 Agent「${row.agent_name}」？`
      : `确定停用 Agent「${row.agent_name}」？停用后该 Agent 的心跳将被拒绝。`,
    confirmText: enabled ? '启用' : '停用',
  })
  if (!confirmed) {
    return
  }
  try {
    if (enabled) {
      await enableAgent(row.id)
    } else {
      await disableAgent(row.id)
    }
    ElMessage.success(enabled ? 'Agent 已启用' : 'Agent 已停用')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

/* ---------- heartbeats ---------- */

const heartbeatAgent = ref<Agent | null>(null)
const heartbeatVisible = ref(false)
const heartbeatHours = ref(24)

const heartbeats = useAsyncData(() =>
  heartbeatAgent.value === null
    ? Promise.resolve(null)
    : listHeartbeats(heartbeatAgent.value.id, 1, 50, heartbeatHours.value),
)

const heartbeatRows = computed(() => heartbeats.data.value?.items ?? [])

function openHeartbeats(row: Agent): void {
  heartbeatAgent.value = row
  heartbeatVisible.value = true
  void heartbeats.reload()
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="Agent" description="采集 Agent 的注册、启用状态与心跳">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openRegister">注册 Agent</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="编码 / 名称"
          clearable
          class="agents__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.status" placeholder="状态" clearable class="agents__field">
          <ElOption v-for="status in AGENT_STATUS" :key="status" :value="status" :label="status" />
        </ElSelect>
        <span class="vctn-muted">仅看启用</span>
        <ElSwitch v-model="filters.enabled" />
      </div>
      <div class="vctn-toolbar__actions">
        <ElButton @click="list.search()">查询</ElButton>
      </div>
    </div>

    <BaseTable
      :rows="list.rows.value"
      :loading="list.loading.value"
      :failed="list.failed.value"
      :error="list.error.value"
      :total="list.total.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      empty-text="没有已注册的 Agent"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="agent_code" label="编码" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="agent_name" label="名称" min-width="160" show-overflow-tooltip />
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }"><StatusTag :value="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElSwitch
            :model-value="row.enabled"
            :disabled="!canManage"
            @update:model-value="toggle(asAgent(row), $event === true)"
          />
        </template>
      </ElTableColumn>
      <ElTableColumn label="版本" width="120">
        <template #default="{ row }">{{ orEmpty(row.version) }}</template>
      </ElTableColumn>
      <ElTableColumn label="IP" width="140">
        <template #default="{ row }">{{ orEmpty(row.ip_address) }}</template>
      </ElTableColumn>
      <ElTableColumn label="最后心跳" width="180">
        <template #default="{ row }">{{ formatDateTime(row.last_heartbeat_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="注册时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.registered_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="openHeartbeats(row)">心跳</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="registerVisible" title="注册 Agent" width="520" @close="closeRegister">
      <template v-if="issuedToken === null">
        <ElForm ref="formRef" :model="form" :rules="rules" label-width="120px">
          <ElFormItem label="Agent 编码" prop="agent_code">
            <ElInput v-model="form.agent_code" />
          </ElFormItem>
          <ElFormItem label="Agent 名称" prop="agent_name">
            <ElInput v-model="form.agent_name" />
          </ElFormItem>
          <ElFormItem label="主机 ID">
            <ElInput v-model="form.host_id" placeholder="选填" />
          </ElFormItem>
          <ElFormItem label="版本">
            <ElInput v-model="form.version" placeholder="选填" />
          </ElFormItem>
        </ElForm>
      </template>

      <template v-else>
        <ElAlert
          type="warning"
          :closable="false"
          show-icon
          title="请立即保存 Token"
          description="后端只保存 Token 的哈希，此处关闭后无法再次查看。"
          class="agents__alert"
        />
        <ElInput :model-value="issuedToken" readonly class="agents__token">
          <template #append>
            <ElButton @click="copyToken">复制</ElButton>
          </template>
        </ElInput>
      </template>

      <template #footer>
        <ElButton v-if="issuedToken === null" @click="closeRegister">取消</ElButton>
        <ElButton v-if="issuedToken === null" type="primary" :loading="submitting" @click="submitRegister">
          注册
        </ElButton>
        <ElButton v-else type="primary" @click="closeRegister">我已保存</ElButton>
      </template>
    </ElDialog>

    <ElDrawer
      v-model="heartbeatVisible"
      :title="`心跳 · ${heartbeatAgent?.agent_name ?? ''}`"
      size="60%"
    >
      <div class="agents__heartbeat-toolbar">
        <ElSelect v-model="heartbeatHours" class="agents__field" @change="heartbeats.reload()">
          <ElOption :value="1" label="近 1 小时" />
          <ElOption :value="24" label="近 24 小时" />
          <ElOption :value="72" label="近 3 天" />
          <ElOption :value="168" label="近 7 天" />
        </ElSelect>
      </div>

      <p v-if="heartbeats.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="heartbeats.failed.value" class="vctn-muted">
        {{ heartbeats.error.value ?? '加载失败' }}
      </p>
      <ElTable v-else :data="heartbeatRows" size="small">
        <ElTableColumn label="采集时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.collected_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="CPU" width="100">
          <template #default="{ row }">{{ orEmpty(row.cpu_usage) }}</template>
        </ElTableColumn>
        <ElTableColumn label="内存" width="100">
          <template #default="{ row }">{{ orEmpty(row.memory_usage) }}</template>
        </ElTableColumn>
        <ElTableColumn label="磁盘" width="100">
          <template #default="{ row }">{{ orEmpty(row.disk_usage) }}</template>
        </ElTableColumn>
        <ElTableColumn label="Load 1/5/15" width="160">
          <template #default="{ row }">
            {{ orEmpty(row.load1) }} / {{ orEmpty(row.load5) }} / {{ orEmpty(row.load15) }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="运行时长 (s)" width="130">
          <template #default="{ row }">{{ orEmpty(row.uptime_seconds) }}</template>
        </ElTableColumn>
        <template #empty><span class="vctn-muted">窗口内没有心跳</span></template>
      </ElTable>
    </ElDrawer>
  </div>
</template>

<style scoped>
.agents__keyword {
  width: 200px;
}

.agents__field {
  width: 140px;
}

.agents__alert {
  margin-bottom: var(--vctn-space-4);
}

.agents__token {
  font-family: var(--vctn-font-mono);
}

.agents__heartbeat-toolbar {
  margin-bottom: var(--vctn-space-3);
}
</style>
