<script setup lang="ts">
/**
 * Alert rules.
 *
 * A rule decides what wakes somebody up, so creating, editing and deleting all
 * require `OPS_ALERT_MANAGE` and the enable switch is a write too — flipping it
 * off silences a whole class of alerts.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import {
  createAlertRule,
  deleteAlertRule,
  listAlertRules,
  updateAlertRule,
} from '@/api/ops/alerts'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { ALERT_CONDITION, ALERT_SEVERITY, SCOPE_TYPE } from '@/types/enums'
import type { AlertRule } from '@/types/ops'
import { formatDateTime } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.alertManage))

const filters = ref({ keyword: '', alertType: '', enabled: undefined as boolean | undefined })

const list = usePagedList<AlertRule>((page, pageSize) =>
  listAlertRules(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    alertType: filters.value.alertType.trim() === '' ? undefined : filters.value.alertType.trim(),
    enabled: filters.value.enabled,
  }),
)

void list.reload()

const editing = ref<AlertRule | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface RuleForm {
  rule_code: string
  rule_name: string
  alert_type: string
  metric_key: string
  condition: string
  threshold: number
  duration_seconds: number
  severity: string
  scope_type: string
  enabled: boolean
}

const form = ref<RuleForm>({
  rule_code: '',
  rule_name: '',
  alert_type: '',
  metric_key: '',
  condition: 'GT',
  threshold: 0,
  duration_seconds: 300,
  severity: 'WARNING',
  scope_type: 'GLOBAL',
  enabled: true,
})

const rules: FormRules<RuleForm> = {
  rule_code: [{ required: true, message: '请输入规则编码', trigger: 'blur' }],
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  alert_type: [{ required: true, message: '请输入告警类型', trigger: 'blur' }],
  metric_key: [{ required: true, message: '请输入指标键', trigger: 'blur' }],
}

function openCreate(): void {
  editing.value = null
  form.value = {
    rule_code: '',
    rule_name: '',
    alert_type: '',
    metric_key: '',
    condition: 'GT',
    threshold: 0,
    duration_seconds: 300,
    severity: 'WARNING',
    scope_type: 'GLOBAL',
    enabled: true,
  }
  dialogVisible.value = true
}

function openEdit(row: AlertRule): void {
  editing.value = row
  form.value = {
    rule_code: row.rule_code,
    rule_name: row.rule_name,
    alert_type: row.alert_type,
    metric_key: row.metric_key,
    condition: row.condition,
    threshold: row.threshold,
    duration_seconds: row.duration_seconds,
    severity: row.severity,
    scope_type: row.scope_type,
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
  submitting.value = true
  try {
    if (editing.value === null) {
      await createAlertRule({
        rule_code: form.value.rule_code.trim(),
        rule_name: form.value.rule_name.trim(),
        alert_type: form.value.alert_type.trim(),
        metric_key: form.value.metric_key.trim(),
        condition: form.value.condition,
        threshold: form.value.threshold,
        duration_seconds: form.value.duration_seconds,
        severity: form.value.severity,
        scope_type: form.value.scope_type,
        enabled: form.value.enabled,
      })
      ElMessage.success('告警规则已创建')
    } else {
      await updateAlertRule(editing.value.id, {
        rule_name: form.value.rule_name.trim(),
        alert_type: form.value.alert_type.trim(),
        metric_key: form.value.metric_key.trim(),
        condition: form.value.condition,
        threshold: form.value.threshold,
        duration_seconds: form.value.duration_seconds,
        severity: form.value.severity,
        scope_type: form.value.scope_type,
        enabled: form.value.enabled,
      })
      ElMessage.success('告警规则已更新')
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
function asAlertRule(row: unknown): AlertRule {
  return row as AlertRule
}

async function toggle(row: AlertRule, enabled: boolean): Promise<void> {
  try {
    await updateAlertRule(row.id, { enabled })
    ElMessage.success(enabled ? '规则已启用' : '规则已停用')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

async function remove(row: AlertRule): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除告警规则',
    message: `确定删除规则「${row.rule_name}」？该操作不可撤销。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteAlertRule(row.id)
    ElMessage.success('告警规则已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="告警规则" description="阈值、持续时长与通知策略">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建规则</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="规则编码 / 名称"
          clearable
          class="alert-rules__keyword"
          @keyup.enter="list.search()"
        />
        <ElInput v-model="filters.alertType" placeholder="告警类型" clearable class="alert-rules__field" />
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
      empty-text="没有匹配的告警规则"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="rule_code" label="规则编码" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="rule_name" label="规则名称" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="alert_type" label="类型" width="130" />
      <ElTableColumn prop="metric_key" label="指标键" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="条件" width="140">
        <template #default="{ row }">{{ row.condition }} {{ row.threshold }}</template>
      </ElTableColumn>
      <ElTableColumn label="持续 (秒)" width="110">
        <template #default="{ row }">{{ row.duration_seconds }}</template>
      </ElTableColumn>
      <ElTableColumn label="级别" width="100">
        <template #default="{ row }"><StatusTag :value="row.severity" /></template>
      </ElTableColumn>
      <ElTableColumn prop="scope_type" label="作用域" width="110" />
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElSwitch
            :model-value="row.enabled"
            :disabled="!canManage"
            @update:model-value="toggle(asAlertRule(row), $event === true)"
          />
        </template>
      </ElTableColumn>
      <ElTableColumn label="更新时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建告警规则' : '编辑告警规则'" width="560">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="130px">
        <ElFormItem label="规则编码" prop="rule_code">
          <ElInput v-model="form.rule_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="规则名称" prop="rule_name">
          <ElInput v-model="form.rule_name" />
        </ElFormItem>
        <ElFormItem label="告警类型" prop="alert_type">
          <ElInput v-model="form.alert_type" />
        </ElFormItem>
        <ElFormItem label="指标键" prop="metric_key">
          <ElInput v-model="form.metric_key" />
        </ElFormItem>
        <ElFormItem label="比较条件">
          <ElSelect v-model="form.condition">
            <ElOption
              v-for="condition in ALERT_CONDITION"
              :key="condition"
              :value="condition"
              :label="condition"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="阈值">
          <ElInputNumber v-model="form.threshold" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="持续时长 (秒)">
          <ElInputNumber v-model="form.duration_seconds" :min="0" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="级别">
          <ElSelect v-model="form.severity">
            <ElOption v-for="level in ALERT_SEVERITY" :key="level" :value="level" :label="level" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="作用域">
          <ElSelect v-model="form.scope_type">
            <ElOption v-for="scope in SCOPE_TYPE" :key="scope" :value="scope" :label="scope" />
          </ElSelect>
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
.alert-rules__keyword {
  width: 220px;
}

.alert-rules__field {
  width: 150px;
}
</style>
