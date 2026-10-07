<script setup lang="ts">
/**
 * Maintenance windows.
 *
 * A window silences alert notifications, so editing one is a high risk action
 * and the write permission is separate from "may view monitoring". The time
 * range is the whole point of the record, which is why it is a single range
 * picker rather than two loose fields.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDatePicker,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import {
  createMaintenanceWindow,
  deleteMaintenanceWindow,
  listMaintenanceWindows,
  updateMaintenanceWindow,
} from '@/api/ops/maintenance'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { SCOPE_TYPE } from '@/types/enums'
import type { MaintenanceWindow } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.maintenanceManage))

const filters = ref({
  keyword: '',
  scopeType: '',
  enabled: undefined as boolean | undefined,
  active: undefined as boolean | undefined,
})

const list = usePagedList<MaintenanceWindow>((page, pageSize) =>
  listMaintenanceWindows(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    scopeType: filters.value.scopeType === '' ? undefined : filters.value.scopeType,
    enabled: filters.value.enabled,
    active: filters.value.active,
  }),
)

void list.reload()

const editing = ref<MaintenanceWindow | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface WindowForm {
  window_code: string
  title: string
  reason: string
  scope_type: string
  scope_id: string
  range: [string, string] | null
  suppress_alerts: boolean
  enabled: boolean
}

const form = ref<WindowForm>({
  window_code: '',
  title: '',
  reason: '',
  scope_type: 'GLOBAL',
  scope_id: '',
  range: null,
  suppress_alerts: true,
  enabled: true,
})

const rules: FormRules<WindowForm> = {
  window_code: [{ required: true, message: '请输入窗口编码', trigger: 'blur' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  range: [{ required: true, message: '请选择时间范围', trigger: 'change' }],
}

function openCreate(): void {
  editing.value = null
  form.value = {
    window_code: '',
    title: '',
    reason: '',
    scope_type: 'GLOBAL',
    scope_id: '',
    range: null,
    suppress_alerts: true,
    enabled: true,
  }
  dialogVisible.value = true
}

function openEdit(row: MaintenanceWindow): void {
  editing.value = row
  form.value = {
    window_code: row.window_code,
    title: row.title,
    reason: row.reason ?? '',
    scope_type: row.scope_type,
    scope_id: row.scope_id ?? '',
    range: [row.starts_at, row.ends_at],
    suppress_alerts: row.suppress_alerts,
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
  if (!valid || form.value.range === null) {
    return
  }
  submitting.value = true
  try {
    if (editing.value === null) {
      await createMaintenanceWindow({
        window_code: form.value.window_code.trim(),
        title: form.value.title.trim(),
        reason: form.value.reason.trim() === '' ? null : form.value.reason.trim(),
        scope_type: form.value.scope_type,
        scope_id: form.value.scope_id.trim() === '' ? null : form.value.scope_id.trim(),
        starts_at: form.value.range[0],
        ends_at: form.value.range[1],
        suppress_alerts: form.value.suppress_alerts,
        enabled: form.value.enabled,
      })
      ElMessage.success('维护窗口已创建')
    } else {
      await updateMaintenanceWindow(editing.value.id, {
        title: form.value.title.trim(),
        reason: form.value.reason.trim() === '' ? null : form.value.reason.trim(),
        scope_type: form.value.scope_type,
        scope_id: form.value.scope_id.trim() === '' ? null : form.value.scope_id.trim(),
        starts_at: form.value.range[0],
        ends_at: form.value.range[1],
        suppress_alerts: form.value.suppress_alerts,
        enabled: form.value.enabled,
      })
      ElMessage.success('维护窗口已更新')
    }
    dialogVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

/** Element Plus hands rows back as a loose record; narrow it for the handler. */
function asMaintenanceWindow(row: unknown): MaintenanceWindow {
  return row as MaintenanceWindow
}

async function toggle(row: MaintenanceWindow, enabled: boolean): Promise<void> {
  try {
    await updateMaintenanceWindow(row.id, { enabled })
    ElMessage.success(enabled ? '窗口已启用' : '窗口已停用')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

async function remove(row: MaintenanceWindow): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除维护窗口',
    message: `确定删除窗口「${row.title}」？该操作不可撤销。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteMaintenanceWindow(row.id)
    ElMessage.success('维护窗口已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="维护窗口" description="在窗口内静默告警，避免计划内维护刷屏">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建窗口</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="编码 / 标题"
          clearable
          class="maintenance__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.scopeType" placeholder="作用域" clearable class="maintenance__field">
          <ElOption v-for="scope in SCOPE_TYPE" :key="scope" :value="scope" :label="scope" />
        </ElSelect>
        <span class="vctn-muted">仅看启用</span>
        <ElSwitch v-model="filters.enabled" />
        <span class="vctn-muted">仅看生效中</span>
        <ElSwitch v-model="filters.active" />
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
      empty-text="没有维护窗口"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="window_code" label="编码" min-width="150" show-overflow-tooltip />
      <ElTableColumn prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <ElTableColumn prop="scope_type" label="作用域" width="110" />
      <ElTableColumn label="开始" width="180">
        <template #default="{ row }">{{ formatDateTime(row.starts_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="结束" width="180">
        <template #default="{ row }">{{ formatDateTime(row.ends_at) }}</template>
      </ElTableColumn>
      <ElTableColumn label="静默告警" width="100">
        <template #default="{ row }">
          <StatusTag :value="row.suppress_alerts" :boolean-labels="['否', '是']" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElSwitch
            :model-value="row.enabled"
            :disabled="!canManage"
            @update:model-value="toggle(asMaintenanceWindow(row), $event === true)"
          />
        </template>
      </ElTableColumn>
      <ElTableColumn label="创建人" width="130">
        <template #default="{ row }">{{ orEmpty(row.created_by_username) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建维护窗口' : '编辑维护窗口'" width="560">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="120px">
        <ElFormItem label="窗口编码" prop="window_code">
          <ElInput v-model="form.window_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="标题" prop="title">
          <ElInput v-model="form.title" />
        </ElFormItem>
        <ElFormItem label="原因">
          <ElInput v-model="form.reason" type="textarea" :rows="2" />
        </ElFormItem>
        <ElFormItem label="作用域">
          <ElSelect v-model="form.scope_type">
            <ElOption v-for="scope in SCOPE_TYPE" :key="scope" :value="scope" :label="scope" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="作用对象 ID">
          <ElInput v-model="form.scope_id" placeholder="选填" />
        </ElFormItem>
        <ElFormItem label="时间范围" prop="range">
          <ElDatePicker
            v-model="form.range"
            type="datetimerange"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            class="maintenance__range"
          />
        </ElFormItem>
        <ElFormItem label="静默告警">
          <ElSwitch v-model="form.suppress_alerts" />
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
.maintenance__keyword {
  width: 200px;
}

.maintenance__field {
  width: 140px;
}

.maintenance__range {
  width: 100%;
}
</style>
