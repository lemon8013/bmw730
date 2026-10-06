<script setup lang="ts">
/** 系统配置：分组筛选配置项，按值类型编辑配置值，敏感值始终以掩码呈现。 */
import { computed, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'

import { listConfigs, updateConfig } from '@/api/config'
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
import { CONFIG_VALUE_TYPE, CONFIG_VALUE_TYPE_LABEL, type ConfigValueType } from '@/types/enums'
import type { SystemConfig, UpdateConfigRequest } from '@/types/system'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.configView)

/** 是否具备配置编辑权限。 */
const canEdit = computed(() => permission.has(PERMISSION.configEdit))

/** 键名或名称疑似凭据的配置，值必须脱敏且不得回填到可编辑输入框。 */
const SENSITIVE_PATTERN = /(secret|password|passwd|token|credential|key)/i
const MASK = '••••••••'

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toConfig(row: Record<string, unknown>): SystemConfig {
  return row as unknown as SystemConfig
}

/** 判断一个配置项是否疑似敏感。 */
function isSensitive(
  config: Pick<SystemConfig, 'config_key' | 'config_name'> | null,
): boolean {
  if (config === null) {
    return false
  }
  return SENSITIVE_PATTERN.test(`${config.config_key} ${config.config_name}`)
}

/** 配置值用于展示：敏感值一律掩码。 */
function displayValue(row: Record<string, unknown>): string {
  const config = toConfig(row)
  if (isSensitive(config)) {
    return MASK
  }
  const value = config.config_value
  return value === null || value === undefined || value === '' ? '—' : value
}

// ---------------------------------------------------------------------------
// 列表与分组筛选
// ---------------------------------------------------------------------------

const selectedGroup = ref<string>('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listConfigs(page.value, pageSize.value),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

/** 分组下拉项来自已加载的行，避免额外请求。 */
const groupOptions = computed<string[]>(() => {
  const groups = new Set<string>()
  for (const item of data.value?.items ?? []) {
    if (item.config_group) {
      groups.add(item.config_group)
    }
  }
  return [...groups].sort()
})

/** 在已加载的行上按分组做本地筛选。 */
const rows = computed(() => {
  const group = selectedGroup.value
  const items = data.value?.items ?? []
  const filtered =
    group === '' ? items : items.filter((item) => (item.config_group ?? '') === group)
  return asRows(filtered)
})

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

function resetFilters(): void {
  selectedGroup.value = ''
  changePage(1)
  void reload()
}

// ---------------------------------------------------------------------------
// 编辑配置值
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const editing = ref<SystemConfig | null>(null)
const editText = ref('')
const editNumber = ref(0)
const editBool = ref(false)
const editReason = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)

/** 当前编辑项的值类型；未知类型回退为字符串。 */
const editValueType = computed<ConfigValueType>(() => {
  const raw = editing.value?.value_type ?? ''
  return CONFIG_VALUE_TYPE.includes(raw as ConfigValueType)
    ? (raw as ConfigValueType)
    : 'STRING'
})

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openEdit(row: Record<string, unknown>): void {
  const config = toConfig(row)
  if (!config.editable) {
    return
  }
  editing.value = config
  // 敏感值不回填：编辑框留空，提交新值即可。
  editText.value = isSensitive(config) ? '' : (config.config_value ?? '')
  const parsed = Number.parseInt(config.config_value ?? '', 10)
  editNumber.value = Number.isFinite(parsed) ? parsed : 0
  editBool.value = (config.config_value ?? '').toLowerCase() === 'true'
  editReason.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

/** 读取当前控件上的值并转换为后端要求的字符串。 */
function readEditedValue(): string {
  if (editValueType.value === 'INT') {
    return String(editNumber.value)
  }
  if (editValueType.value === 'BOOL') {
    return editBool.value ? 'true' : 'false'
  }
  return editText.value
}

async function submit(): Promise<void> {
  const config = editing.value
  if (config === null) {
    return
  }
  clearSubmitError()
  const value = readEditedValue()
  if (isSensitive(config) && value.trim() === '') {
    submitError.value = '敏感配置值不能为空，请输入新的值'
    return
  }
  submitting.value = true
  try {
    const payload: UpdateConfigRequest = {
      config_value: value,
      reason: editReason.value.trim() === '' ? null : editReason.value.trim(),
    }
    await updateConfig(config.config_key, payload)
    notify.success('配置已更新')
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    const rendered = renderError(caught)
    submitError.value = rendered.message
    submitTrace.value = rendered.traceId ?? null
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="config-page">
    <PageHeader
      title="系统配置"
      description="查看并维护系统运行参数；敏感配置值以掩码展示，且不会回填到编辑框。"
    >
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="config-page__filters">
      <ElSpace wrap>
        <ElSelect
          v-model="selectedGroup"
          placeholder="按分组筛选"
          clearable
          style="width: 220px"
        >
          <ElOption
            v-for="group in groupOptions"
            :key="group"
            :label="group"
            :value="group"
          />
        </ElSelect>
        <ElButton @click="resetFilters">重置</ElButton>
      </ElSpace>
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
        row-key="config_key"
        empty-text="暂无配置项"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('config_key')"
          prop="config_key"
          label="配置键"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('config_name')"
          prop="config_name"
          label="名称"
          min-width="160"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('config_group')"
          prop="config_group"
          label="分组"
          width="130"
        />
        <ElTableColumn
          v-if="!fields.isHidden('value_type')"
          prop="value_type"
          label="值类型"
          width="100"
        >
          <template #default="{ row }">
            <StatusTag :value="row.value_type" :labels="CONFIG_VALUE_TYPE_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('config_value')"
          label="配置值"
          min-width="200"
          show-overflow-tooltip
        >
          <template #default="{ row }">{{ displayValue(row) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('editable')"
          prop="editable"
          label="可编辑"
          width="90"
        >
          <template #default="{ row }">
            <StatusTag :value="row.editable" :boolean-labels="['否', '是']" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('requires_restart')"
          prop="requires_restart"
          label="需重启"
          width="90"
        >
          <template #default="{ row }">
            <StatusTag :value="row.requires_restart" :boolean-labels="['否', '是']" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('version')" prop="version" label="版本" width="80" />
        <ElTableColumn
          v-if="!fields.isHidden('updated_at')"
          label="更新时间"
          width="180"
        >
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canEdit" label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton
              v-permission="PERMISSION.configEdit"
              link
              type="primary"
              :disabled="!row.editable"
              @click="openEdit(row)"
            >
              编辑
            </ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      title="编辑配置值"
      :confirm-loading="submitting"
      confirm-text="保存"
      width="560px"
      @confirm="submit"
    >
      <BaseForm
        :model="{ config_value: editText, reason: editReason }"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem label="配置键">
          <span class="config-page__readonly">{{ editing?.config_key ?? '—' }}</span>
        </ElFormItem>
        <ElFormItem label="当前值">
          <span class="config-page__readonly">
            {{ editing && isSensitive(editing) ? MASK : (editing?.config_value ?? '—') }}
          </span>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('config_value')" label="配置值">
          <ElInputNumber
            v-if="editValueType === 'INT'"
            v-model="editNumber"
            :disabled="fields.isReadOnly('config_value')"
          />
          <ElSwitch
            v-else-if="editValueType === 'BOOL'"
            v-model="editBool"
            :disabled="fields.isReadOnly('config_value')"
          />
          <ElInput
            v-else
            v-model="editText"
            :show-password="isSensitive(editing)"
            :disabled="fields.isReadOnly('config_value')"
            :placeholder="
              isSensitive(editing) ? '当前值已隐藏，请输入新的值' : '请输入配置值'
            "
          />
        </ElFormItem>
        <ElFormItem label="变更原因">
          <ElInput
            v-model="editReason"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('config_value')"
            placeholder="可选，便于审计追溯"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.config-page__filters {
  margin-bottom: 16px;
}

.config-page__readonly {
  color: var(--vctn-text-regular);
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  word-break: break-all;
}
</style>
