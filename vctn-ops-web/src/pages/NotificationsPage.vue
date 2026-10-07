<script setup lang="ts">
/**
 * Notification attempts and channels.
 *
 * Two different things share one screen because they are read together: the
 * record of what was sent, and the channels it was sent through. Channel
 * `config` never contains a credential, so it is safe to show as JSON.
 */
import { computed, ref, watch } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTabPane,
  ElTabs,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import {
  createNotificationChannel,
  listNotificationChannels,
  listNotifications,
  updateNotificationChannel,
} from '@/api/ops/notifications'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import type { AlertNotification, NotificationChannel } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.alertManage))

const tab = ref('records')

/* ---------- notification records ---------- */

const recordFilters = ref({ status: '', alertId: '' })

const records = usePagedList<AlertNotification>((page, pageSize) =>
  listNotifications(
    page,
    pageSize,
    recordFilters.value.status === '' ? undefined : recordFilters.value.status,
    recordFilters.value.alertId.trim() === '' ? undefined : recordFilters.value.alertId.trim(),
  ),
)

/* ---------- notification channels ---------- */

const channelFilters = ref({ keyword: '', channelType: '', enabled: undefined as boolean | undefined })

const channels = usePagedList<NotificationChannel>((page, pageSize) =>
  listNotificationChannels(page, pageSize, {
    keyword: channelFilters.value.keyword.trim() === '' ? undefined : channelFilters.value.keyword.trim(),
    channelType: channelFilters.value.channelType === '' ? undefined : channelFilters.value.channelType,
    enabled: channelFilters.value.enabled,
  }),
)

// The two lists are independent, so each is loaded the first time its tab opens
// rather than firing both requests on every visit.
watch(
  tab,
  (value) => {
    if (value === 'records' && records.rows.value.length === 0 && !records.loading.value) {
      void records.reload()
    }
    if (value === 'channels' && channels.rows.value.length === 0 && !channels.loading.value) {
      void channels.reload()
    }
  },
  { immediate: true },
)

/* ---------- channel dialog ---------- */

const CHANNEL_TYPES = ['WEBHOOK', 'EMAIL', 'SMS', 'DINGTALK', 'WECOM'] as const

const editing = ref<NotificationChannel | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface ChannelForm {
  channel_code: string
  channel_name: string
  channel_type: string
  config: string
  enabled: boolean
}

const form = ref<ChannelForm>({
  channel_code: '',
  channel_name: '',
  channel_type: 'WEBHOOK',
  config: '{}',
  enabled: true,
})

const rules: FormRules<ChannelForm> = {
  channel_code: [{ required: true, message: '请输入渠道编码', trigger: 'blur' }],
  channel_name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }],
  config: [{ required: true, message: '请输入渠道配置 JSON', trigger: 'blur' }],
}

/** Parse the JSON textarea; returns `null` when it is not an object. */
function parseConfig(raw: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(raw)
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return null
    }
    return parsed as Record<string, unknown>
  } catch {
    return null
  }
}

function openCreate(): void {
  editing.value = null
  form.value = {
    channel_code: '',
    channel_name: '',
    channel_type: 'WEBHOOK',
    config: '{}',
    enabled: true,
  }
  dialogVisible.value = true
}

function openEdit(row: NotificationChannel): void {
  editing.value = row
  form.value = {
    channel_code: row.channel_code,
    channel_name: row.channel_name,
    channel_type: row.channel_type,
    config: JSON.stringify(row.config ?? {}, null, 2),
    enabled: row.enabled,
  }
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  const instance = formRef.value
  if (instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  const config = parseConfig(form.value.config)
  if (config === null) {
    ElMessage.warning('渠道配置必须是一个 JSON 对象')
    return
  }
  submitting.value = true
  try {
    if (editing.value === null) {
      await createNotificationChannel({
        channel_code: form.value.channel_code.trim(),
        channel_name: form.value.channel_name.trim(),
        channel_type: form.value.channel_type,
        config,
        enabled: form.value.enabled,
      })
      ElMessage.success('通知渠道已创建')
    } else {
      await updateNotificationChannel(editing.value.id, {
        channel_name: form.value.channel_name.trim(),
        channel_type: form.value.channel_type,
        config,
        enabled: form.value.enabled,
      })
      ElMessage.success('通知渠道已更新')
    }
    dialogVisible.value = false
    await channels.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

/** Element Plus hands rows back as a loose record; narrow it for the handler. */
function asNotificationChannel(row: unknown): NotificationChannel {
  return row as NotificationChannel
}

async function toggle(row: NotificationChannel, enabled: boolean): Promise<void> {
  try {
    await updateNotificationChannel(row.id, { enabled })
    ElMessage.success(enabled ? '渠道已启用' : '渠道已停用')
    await channels.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="通知中心" description="告警通知的投递记录与通知渠道" />

    <ElTabs v-model="tab">
      <ElTabPane label="投递记录" name="records">
        <div class="vctn-toolbar">
          <div class="vctn-toolbar__filters">
            <ElInput v-model="recordFilters.status" placeholder="状态" clearable class="notifications__field" />
            <ElInput
              v-model="recordFilters.alertId"
              placeholder="告警 ID"
              clearable
              class="notifications__field"
              @keyup.enter="records.search()"
            />
          </div>
          <div class="vctn-toolbar__actions">
            <ElButton @click="records.search()">查询</ElButton>
          </div>
        </div>

        <BaseTable
          :rows="records.rows.value"
          :loading="records.loading.value"
          :failed="records.failed.value"
          :error="records.error.value"
          :total="records.total.value"
          :page="records.page.value"
          :page-size="records.pageSize.value"
          empty-text="没有投递记录"
          @retry="records.reload()"
          @update:page="records.changePage"
          @update:page-size="records.changePageSize"
        >
          <ElTableColumn prop="channel_code" label="渠道" min-width="160" />
          <ElTableColumn label="状态" width="110">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </ElTableColumn>
          <ElTableColumn label="接收方" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ orEmpty(row.receiver) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="retry_count" label="重试次数" width="110" />
          <ElTableColumn label="发送时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.sent_at) }}</template>
          </ElTableColumn>
          <ElTableColumn prop="error_message" label="错误" min-width="200" show-overflow-tooltip />
        </BaseTable>
      </ElTabPane>

      <ElTabPane label="通知渠道" name="channels">
        <div class="vctn-toolbar">
          <div class="vctn-toolbar__filters">
            <ElInput
              v-model="channelFilters.keyword"
              placeholder="渠道编码 / 名称"
              clearable
              class="notifications__keyword"
              @keyup.enter="channels.search()"
            />
            <ElSelect
              v-model="channelFilters.channelType"
              placeholder="类型"
              clearable
              class="notifications__field"
            >
              <ElOption v-for="type in CHANNEL_TYPES" :key="type" :value="type" :label="type" />
            </ElSelect>
            <span class="vctn-muted">仅看启用</span>
            <ElSwitch v-model="channelFilters.enabled" />
          </div>
          <div class="vctn-toolbar__actions">
            <ElButton @click="channels.search()">查询</ElButton>
            <ElButton v-if="canManage" type="primary" @click="openCreate">新建渠道</ElButton>
          </div>
        </div>

        <BaseTable
          :rows="channels.rows.value"
          :loading="channels.loading.value"
          :failed="channels.failed.value"
          :error="channels.error.value"
          :total="channels.total.value"
          :page="channels.page.value"
          :page-size="channels.pageSize.value"
          empty-text="没有通知渠道"
          @retry="channels.reload()"
          @update:page="channels.changePage"
          @update:page-size="channels.changePageSize"
        >
          <ElTableColumn prop="channel_code" label="渠道编码" min-width="150" />
          <ElTableColumn prop="channel_name" label="渠道名称" min-width="160" />
          <ElTableColumn prop="channel_type" label="类型" width="120" />
          <ElTableColumn label="启用" width="90">
            <template #default="{ row }">
              <ElSwitch
                :model-value="row.enabled"
                :disabled="!canManage"
                @update:model-value="toggle(asNotificationChannel(row), $event === true)"
              />
            </template>
          </ElTableColumn>
          <ElTableColumn label="更新时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
          </ElTableColumn>

          <template #operations="{ row }">
            <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
          </template>
        </BaseTable>
      </ElTabPane>
    </ElTabs>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建通知渠道' : '编辑通知渠道'" width="560">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="120px">
        <ElFormItem label="渠道编码" prop="channel_code">
          <ElInput v-model="form.channel_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="渠道名称" prop="channel_name">
          <ElInput v-model="form.channel_name" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElSelect v-model="form.channel_type">
            <ElOption v-for="type in CHANNEL_TYPES" :key="type" :value="type" :label="type" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="配置 JSON" prop="config">
          <ElInput v-model="form.config" type="textarea" :rows="6" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.notifications__keyword {
  width: 220px;
}

.notifications__field {
  width: 150px;
}
</style>
