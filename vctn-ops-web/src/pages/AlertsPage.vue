<script setup lang="ts">
/**
 * Alerts.
 *
 * Acknowledging, silencing and resolving each need their own permission and
 * each change what the platform tells people, so all three ask first. Silencing
 * additionally needs a duration and a reason: an unexplained silence window is
 * indistinguishable from an outage nobody noticed.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import { acknowledgeAlert, listAlerts, resolveAlert, silenceAlert } from '@/api/ops/alerts'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { ALERT_SEVERITY, ALERT_STATUS } from '@/types/enums'
import type { Alert } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()

const canAck = computed(() => permission.has(OPS_PERMISSION.alertAck))
const canSilence = computed(() => permission.has(OPS_PERMISSION.alertSilence))
const canManage = computed(() => permission.has(OPS_PERMISSION.alertManage))

const filters = ref({
  status: '',
  severity: '',
  alertType: '',
  range: null as [string, string] | null,
})

const list = usePagedList<Alert>((page, pageSize) =>
  listAlerts(page, pageSize, {
    status: filters.value.status === '' ? undefined : filters.value.status,
    severity: filters.value.severity === '' ? undefined : filters.value.severity,
    alertType: filters.value.alertType.trim() === '' ? undefined : filters.value.alertType.trim(),
    start: filters.value.range?.[0] ?? null,
    end: filters.value.range?.[1] ?? null,
  }),
)

void list.reload()

/** The alert an action dialog is open for. */
const target = ref<Alert | null>(null)
const ackVisible = ref(false)
const silenceVisible = ref(false)
const submitting = ref(false)

const ackForm = ref({ note: '' })

const silenceFormRef = ref<FormInstance>()
const silenceForm = ref({ silence_minutes: 60, silence_reason: '' })
const silenceRules: FormRules<typeof silenceForm.value> = {
  silence_minutes: [{ required: true, message: '请输入静默时长', trigger: 'blur' }],
  silence_reason: [{ required: true, message: '请输入静默原因', trigger: 'blur' }],
}

function openAck(row: Alert): void {
  target.value = row
  ackForm.value.note = ''
  ackVisible.value = true
}

function openSilence(row: Alert): void {
  target.value = row
  silenceForm.value = { silence_minutes: 60, silence_reason: '' }
  silenceVisible.value = true
}

async function submitAck(): Promise<void> {
  const alert = target.value
  if (alert === null) {
    return
  }
  submitting.value = true
  try {
    await acknowledgeAlert(alert.id, {
      note: ackForm.value.note.trim() === '' ? null : ackForm.value.note.trim(),
    })
    ElMessage.success('告警已认领')
    ackVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function submitSilence(): Promise<void> {
  const alert = target.value
  const instance = silenceFormRef.value
  if (alert === null || instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    await silenceAlert(alert.id, {
      silence_minutes: silenceForm.value.silence_minutes,
      silence_reason: silenceForm.value.silence_reason.trim(),
    })
    ElMessage.success('告警已静默')
    silenceVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function resolve(row: Alert): Promise<void> {
  const confirmed = await confirmAction({
    title: '恢复告警',
    message: `确定将告警「${row.description || row.fingerprint}」标记为已恢复？`,
    confirmText: '恢复',
  })
  if (!confirmed) {
    return
  }
  try {
    await resolveAlert(row.id, { note: null })
    ElMessage.success('告警已恢复')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="告警中心" description="告警实例的认领、静默与恢复" />

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElSelect v-model="filters.status" placeholder="状态" clearable class="alerts__field">
          <ElOption v-for="status in ALERT_STATUS" :key="status" :value="status" :label="status" />
        </ElSelect>
        <ElSelect v-model="filters.severity" placeholder="级别" clearable class="alerts__field">
          <ElOption v-for="level in ALERT_SEVERITY" :key="level" :value="level" :label="level" />
        </ElSelect>
        <ElInput v-model="filters.alertType" placeholder="告警类型" clearable class="alerts__field" />
        <ElDatePicker
          v-model="filters.range"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          value-format="YYYY-MM-DDTHH:mm:ss"
          class="alerts__range"
        />
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
      empty-text="没有匹配的告警"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn label="级别" width="100">
        <template #default="{ row }"><StatusTag :value="row.severity" /></template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="120">
        <template #default="{ row }"><StatusTag :value="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn prop="alert_type" label="类型" width="130" />
      <ElTableColumn prop="description" label="描述" min-width="240" show-overflow-tooltip />
      <ElTableColumn label="指标 / 阈值" min-width="180">
        <template #default="{ row }">
          <span v-if="row.metric_key">
            {{ row.metric_key }} {{ orEmpty(row.metric_value) }} / {{ orEmpty(row.threshold) }}
          </span>
          <span v-else class="vctn-muted">—</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="触发时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.triggered_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="认领时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.acknowledged_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="静默至" width="180">
        <template #default="{ row }">{{ formatDateTime(row.silenced_until) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton v-if="canAck" link type="primary" @click="openAck(row)">认领</ElButton>
        <ElButton v-if="canSilence" link type="warning" @click="openSilence(row)">静默</ElButton>
        <ElButton v-if="canManage" link type="success" @click="resolve(row)">恢复</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="ackVisible" title="认领告警" width="480">
      <ElForm ref="ackFormRef" :model="ackForm" label-width="90px">
        <ElFormItem label="备注">
          <ElInput v-model="ackForm.note" type="textarea" :rows="3" placeholder="选填" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="ackVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitAck">确认认领</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="silenceVisible" title="静默告警" width="480">
      <ElForm ref="silenceFormRef" :model="silenceForm" :rules="silenceRules" label-width="110px">
        <ElFormItem label="静默时长 (分钟)" prop="silence_minutes">
          <ElInputNumber v-model="silenceForm.silence_minutes" :min="1" :max="10080" />
        </ElFormItem>
        <ElFormItem label="静默原因" prop="silence_reason">
          <ElInput v-model="silenceForm.silence_reason" type="textarea" :rows="3" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="silenceVisible = false">取消</ElButton>
        <ElButton type="warning" :loading="submitting" @click="submitSilence">确认静默</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.alerts__field {
  width: 150px;
}

.alerts__range {
  width: 360px;
}
</style>
