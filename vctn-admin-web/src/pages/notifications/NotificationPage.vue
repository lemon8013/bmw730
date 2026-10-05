<script setup lang="ts">
/** 通知管理：按条件检索通知、发送新通知、标记已读，并查看分类统计。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElDatePicker,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'

import {
  getNotificationStats,
  listNotifications,
  markNotificationRead,
  sendNotification,
} from '@/api/notifications'
import JsonViewer from '@/components/common/JsonViewer.vue'
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
import {
  NOTIFICATION_TYPE,
  NOTIFICATION_TYPE_LABEL,
  NOTIFICATION_USER_TYPE,
  NOTIFICATION_USER_TYPE_LABEL,
} from '@/types/enums'
import type { NotificationType, NotificationUserType } from '@/types/enums'
import type {
  CreateNotificationRequest,
  Notification,
  NotificationQuery,
} from '@/types/ops'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.notificationView)

/** 是否具备发送通知权限。 */
const canSend = permission.has(PERMISSION.notificationSend)
/** 是否具备标记已读权限。 */
const canMarkRead = permission.has(PERMISSION.notificationManage)

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

function isUnread(row: Record<string, unknown>): boolean {
  return row.read_at === null || row.read_at === undefined
}

/** 通知类型的中文标签；未知码回退为原始值。 */
function notificationTypeLabel(value: unknown): string {
  const raw = String(value ?? '')
  return NOTIFICATION_TYPE_LABEL[raw as NotificationType] ?? raw
}

/** 用户类型的中文标签；未知码回退为原始值。 */
function userTypeLabel(value: unknown): string {
  const raw = String(value ?? '')
  return NOTIFICATION_USER_TYPE_LABEL[raw as NotificationUserType] ?? raw
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  user_type: string
  user_id: string
  notification_type: string
  unread_only: boolean
  dateRange: [string, string] | null
}>({
  user_type: '',
  user_id: '',
  notification_type: '',
  unread_only: false,
  dateRange: null,
})

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

function buildQuery(): NotificationQuery {
  const range = filters.dateRange
  return {
    user_type: filters.user_type === '' ? undefined : filters.user_type,
    user_id: filters.user_id.trim() === '' ? undefined : filters.user_id.trim(),
    notification_type:
      filters.notification_type === '' ? undefined : filters.notification_type,
    unread_only: filters.unread_only,
    start: range === null ? undefined : range[0],
    end: range === null ? undefined : range[1],
    page: page.value,
    page_size: pageSize.value,
  }
}

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listNotifications(buildQuery()),
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
  filters.user_type = ''
  filters.user_id = ''
  filters.notification_type = ''
  filters.unread_only = false
  filters.dateRange = null
  search()
}

// ---------------------------------------------------------------------------
// 统计
// ---------------------------------------------------------------------------

const {
  data: statData,
  loading: statsLoading,
  failed: statsFailed,
  error: statsError,
  reload: reloadStats,
} = useAsyncData(() => getNotificationStats())

const statRows = computed(() => asRows(statData.value ?? []))

function refreshAll(): void {
  void reload()
  void reloadStats()
}

// ---------------------------------------------------------------------------
// 发送通知
// ---------------------------------------------------------------------------

interface SendFormModel {
  user_type: string
  user_id: string
  notification_type: string
  title: string
  content: string
}

const sendModel = reactive<SendFormModel>({
  user_type: 'SYS_USER',
  user_id: '',
  notification_type: 'SYSTEM',
  title: '',
  content: '',
})

const sendVisible = ref(false)
const sending = ref(false)
const sendError = ref<string | null>(null)
const sendTrace = ref<string | null>(null)

function openSend(): void {
  sendModel.user_type = 'SYS_USER'
  sendModel.user_id = ''
  sendModel.notification_type = 'SYSTEM'
  sendModel.title = ''
  sendModel.content = ''
  sendError.value = null
  sendTrace.value = null
  sendVisible.value = true
}

async function submitSend(): Promise<void> {
  sendError.value = null
  sendTrace.value = null
  if (sendModel.user_id.trim() === '') {
    sendError.value = '请填写接收用户 ID'
    return
  }
  if (sendModel.title.trim() === '') {
    sendError.value = '请填写通知标题'
    return
  }
  if (sendModel.content.trim() === '') {
    sendError.value = '请填写通知内容'
    return
  }
  sending.value = true
  try {
    const payload: CreateNotificationRequest = {
      user_type: sendModel.user_type,
      user_id: sendModel.user_id.trim(),
      notification_type: sendModel.notification_type,
      title: sendModel.title.trim(),
      content: sendModel.content.trim(),
    }
    await sendNotification(payload)
    notify.success('通知已发送')
    sendVisible.value = false
    await reload()
  } catch (caught) {
    const rendered = renderError(caught)
    sendError.value = rendered.message
    sendTrace.value = rendered.traceId ?? null
  } finally {
    sending.value = false
  }
}

// ---------------------------------------------------------------------------
// 标记已读
// ---------------------------------------------------------------------------

async function onMarkRead(row: Record<string, unknown>): Promise<void> {
  try {
    await markNotificationRead(String(row.id))
    notify.success('已标记为已读')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 通知内容查看
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const activeNotification = ref<Notification | null>(null)

function openDetail(row: Record<string, unknown>): void {
  activeNotification.value = row as unknown as Notification
  detailVisible.value = true
}
</script>

<template>
  <div class="notification-page">
    <PageHeader title="通知管理" description="检索、发送站内通知，并查看各类型通知的已读 / 未读统计。">
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
        <ElButton v-if="canSend" v-permission="PERMISSION.notificationSend" type="primary" @click="openSend">
          发送通知
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="notification-page__filters">
      <ElSpace wrap>
        <ElSelect v-model="filters.user_type" placeholder="用户类型" clearable style="width: 150px">
          <ElOption
            v-for="item in NOTIFICATION_USER_TYPE"
            :key="item"
            :label="NOTIFICATION_USER_TYPE_LABEL[item]"
            :value="item"
          />
        </ElSelect>
        <ElInput
          v-model="filters.user_id"
          placeholder="用户 ID"
          clearable
          style="width: 180px"
        />
        <ElSelect
          v-model="filters.notification_type"
          placeholder="通知类型"
          clearable
          style="width: 180px"
        >
          <ElOption
            v-for="item in NOTIFICATION_TYPE"
            :key="item"
            :label="NOTIFICATION_TYPE_LABEL[item]"
            :value="item"
          />
        </ElSelect>
        <ElDatePicker
          v-model="filters.dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <span class="notification-page__switch">
          <span>仅未读</span>
          <ElSwitch v-model="filters.unread_only" />
        </span>
        <ElButton type="primary" @click="search">查询</ElButton>
        <ElButton @click="resetFilters">重置</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never" class="notification-page__stats">
      <template #header>通知统计</template>
      <BaseTable
        :rows="statRows"
        :loading="statsLoading"
        :failed="statsFailed"
        :error="statsError"
        :total="0"
        :page="1"
        :page-size="1"
        :paginated="false"
        row-key="notification_type"
        empty-text="暂无统计数据"
        @retry="reloadStats"
      >
        <ElTableColumn label="通知类型" min-width="180">
          <template #default="{ row }">{{ notificationTypeLabel(row.notification_type) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="total" label="总数" width="120" />
        <ElTableColumn prop="unread" label="未读数" width="120" />
      </BaseTable>
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
        empty-text="暂无通知"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('title')"
          prop="title"
          label="标题"
          min-width="180"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('notification_type')" label="类型" width="150">
          <template #default="{ row }">{{ notificationTypeLabel(row.notification_type) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('user_type')" label="用户类型" width="120">
          <template #default="{ row }">{{ userTypeLabel(row.user_type) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('user_id')" prop="user_id" label="用户 ID" width="160" />
        <ElTableColumn v-if="!fields.isHidden('content')" label="内容" min-width="200">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row)">查看</ElButton>
          </template>
        </ElTableColumn>
        <ElTableColumn label="读取状态" width="110">
          <template #default="{ row }">
            <StatusTag :value="!isUnread(row)" :boolean-labels="['未读', '已读']" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="读取时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.read_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canMarkRead" label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <ElButton
              v-if="isUnread(row)"
              v-permission="PERMISSION.notificationManage"
              link
              type="primary"
              @click="onMarkRead(row)"
            >
              标记已读
            </ElButton>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="sendVisible"
      title="发送通知"
      :confirm-loading="sending"
      confirm-text="发送"
      width="560px"
      @confirm="submitSend"
    >
      <BaseForm
        :model="sendModel"
        :error-message="sendError"
        :error-trace-id="sendTrace"
        hide-footer
      >
        <ElFormItem label="用户类型">
          <ElSelect v-model="sendModel.user_type" style="width: 100%">
            <ElOption
              v-for="item in NOTIFICATION_USER_TYPE"
              :key="item"
              :label="NOTIFICATION_USER_TYPE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="用户 ID">
          <ElInput v-model="sendModel.user_id" placeholder="接收者的用户 ID" />
        </ElFormItem>
        <ElFormItem label="通知类型">
          <ElSelect v-model="sendModel.notification_type" style="width: 100%">
            <ElOption
              v-for="item in NOTIFICATION_TYPE"
              :key="item"
              :label="NOTIFICATION_TYPE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="标题">
          <ElInput v-model="sendModel.title" />
        </ElFormItem>
        <ElFormItem label="内容">
          <ElInput v-model="sendModel.content" type="textarea" :rows="3" />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <BaseDialog v-model="detailVisible" title="通知内容" width="560px" hide-footer>
      <div v-if="activeNotification" class="notification-page__detail">
        <p><strong>标题：</strong>{{ activeNotification.title }}</p>
        <p><strong>类型：</strong>{{ notificationTypeLabel(activeNotification.notification_type) }}</p>
        <p><strong>用户类型：</strong>{{ userTypeLabel(activeNotification.user_type) }}</p>
        <p><strong>创建时间：</strong>{{ formatDateTime(activeNotification.created_at) }}</p>
        <p><strong>内容：</strong>{{ activeNotification.content }}</p>
        <p v-if="activeNotification.payload"><strong>附加数据：</strong></p>
        <JsonViewer v-if="activeNotification.payload" :value="activeNotification.payload" />
      </div>
    </BaseDialog>
  </div>
</template>

<style scoped>
.notification-page__filters {
  margin-bottom: 16px;
}

.notification-page__switch {
  display: inline-flex;
  gap: 6px;
  align-items: center;
}

.notification-page__stats {
  margin-bottom: 16px;
}

.notification-page__detail p {
  margin: 0 0 8px;
}
</style>
