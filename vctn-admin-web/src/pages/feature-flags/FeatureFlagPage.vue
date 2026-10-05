<script setup lang="ts">
/** 功能开关管理：列表、创建、编辑、启用与禁用。 */
import { computed, reactive, ref, watch } from 'vue'
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
  type FormRules,
} from 'element-plus'

import {
  createFeatureFlag,
  disableFeatureFlag,
  enableFeatureFlag,
  listFeatureFlags,
  updateFeatureFlag,
} from '@/api/featureFlags'
import DataStateView from '@/components/common/DataStateView.vue'
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
import { FEATURE_FLAG_STRATEGY, FEATURE_FLAG_STRATEGY_LABEL } from '@/types/enums'
import type { CreateFeatureFlagRequest, FeatureFlag, UpdateFeatureFlagRequest } from '@/types/system'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.featureFlagView)

/** 是否具备功能开关的编辑权限。 */
const canEdit = computed(() => permission.has(PERMISSION.featureFlagEdit))

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

/** 列表筛选状态。 */
const filters = reactive<{ keyword: string }>({ keyword: '' })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listFeatureFlags(page.value, pageSize.value),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

const rows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  const items = data.value?.items ?? []
  const filtered =
    keyword === ''
      ? items
      : items.filter(
          (item) =>
            item.flag_key.toLowerCase().includes(keyword) ||
            item.flag_name.toLowerCase().includes(keyword),
        )
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

function search(): void {
  changePage(1)
  void reload()
}

function resetFilters(): void {
  filters.keyword = ''
  search()
}

// ---------------------------------------------------------------------------
// 新建 / 编辑
// ---------------------------------------------------------------------------

interface FlagFormModel {
  flag_key: string
  flag_name: string
  enabled: boolean
  strategy: string
  percentage: number
  description: string
}

const formModel = reactive<FlagFormModel>({
  flag_key: '',
  flag_name: '',
  enabled: false,
  strategy: 'GLOBAL',
  percentage: 0,
  description: '',
})

const conditionsText = ref('')
const rules: FormRules = {
  flag_key: [{ required: true, message: '请输入开关标识', trigger: 'blur' }],
  flag_name: [{ required: true, message: '请输入开关名称', trigger: 'blur' }],
}

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openCreate(): void {
  editingId.value = null
  formModel.flag_key = ''
  formModel.flag_name = ''
  formModel.enabled = false
  formModel.strategy = 'GLOBAL'
  formModel.percentage = 0
  formModel.description = ''
  conditionsText.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const flag = row as unknown as FeatureFlag
  editingId.value = flag.id
  formModel.flag_key = flag.flag_key
  formModel.flag_name = flag.flag_name
  formModel.enabled = flag.enabled
  formModel.strategy = flag.strategy
  formModel.percentage = flag.percentage
  formModel.description = flag.description ?? ''
  conditionsText.value = flag.conditions ? JSON.stringify(flag.conditions, null, 2) : ''
  clearSubmitError()
  dialogVisible.value = true
}

function reportSubmitError(caught: unknown): void {
  const rendered = renderError(caught)
  submitError.value = rendered.message
  submitTrace.value = rendered.traceId ?? null
}

/** 读取条件文本框；`undefined` 表示校验失败，`null` 表示未配置条件。 */
function readConditions(): Record<string, unknown> | null | undefined {
  const text = conditionsText.value.trim()
  if (text === '') {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(text)
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      submitError.value = '条件必须是一个 JSON 对象'
      return undefined
    }
    return parsed as Record<string, unknown>
  } catch {
    submitError.value = '条件不是合法的 JSON'
    return undefined
  }
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  const conditions = readConditions()
  if (conditions === undefined) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    if (editingId.value === null) {
      const payload: CreateFeatureFlagRequest = {
        flag_key: formModel.flag_key,
        flag_name: formModel.flag_name,
        enabled: formModel.enabled,
        strategy: formModel.strategy,
        percentage: formModel.percentage,
        conditions,
        description: formModel.description.trim() === '' ? null : formModel.description.trim(),
      }
      await createFeatureFlag(payload)
      notify.success('功能开关已创建')
    } else {
      const payload: UpdateFeatureFlagRequest = {
        flag_name: formModel.flag_name,
        strategy: formModel.strategy,
        percentage: formModel.percentage,
        conditions,
        description: formModel.description.trim() === '' ? null : formModel.description.trim(),
      }
      await updateFeatureFlag(editingId.value, payload)
      notify.success('功能开关已更新')
    }
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 启用 / 禁用
// ---------------------------------------------------------------------------

async function onEnable(row: Record<string, unknown>): Promise<void> {
  try {
    await enableFeatureFlag(String(row.id))
    notify.success('功能开关已启用')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDisable(row: Record<string, unknown>): Promise<void> {
  const name = String(row.flag_name ?? '')
  const confirmed = await notify.confirm({
    title: '禁用功能开关',
    message: `确定要禁用「${name}」吗？该开关覆盖的功能将立即对所有用户关闭。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await disableFeatureFlag(String(row.id))
    notify.success('功能开关已禁用')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 条件查看
// ---------------------------------------------------------------------------

const conditionsVisible = ref(false)
const activeConditions = ref<Record<string, unknown> | null>(null)

function openConditions(row: Record<string, unknown>): void {
  const raw = row.conditions
  activeConditions.value =
    raw !== null && typeof raw === 'object' && !Array.isArray(raw)
      ? (raw as Record<string, unknown>)
      : null
  conditionsVisible.value = true
}
</script>

<template>
  <div class="feature-flag-page">
    <PageHeader title="功能开关" description="按策略灰度发布功能，支持全量、用户、等级、百分比与条件策略。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-permission="PERMISSION.featureFlagEdit" type="primary" @click="openCreate">
          新建开关
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="feature-flag-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="filters.keyword"
          placeholder="按标识或名称搜索"
          clearable
          style="width: 240px"
          @keyup.enter="search"
        />
        <ElButton type="primary" @click="search">查询</ElButton>
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
        empty-text="暂无功能开关"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('flag_key')"
          prop="flag_key"
          label="开关标识"
          min-width="180"
        />
        <ElTableColumn
          v-if="!fields.isHidden('flag_name')"
          prop="flag_name"
          label="名称"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('enabled')"
          prop="enabled"
          label="状态"
          width="96"
        >
          <template #default="{ row }">
            <StatusTag :value="row.enabled" :boolean-labels="['禁用', '启用']" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('strategy')"
          prop="strategy"
          label="策略"
          width="130"
        >
          <template #default="{ row }">
            <StatusTag :value="row.strategy" :labels="FEATURE_FLAG_STRATEGY_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('percentage')" label="百分比" width="96">
          <template #default="{ row }">{{ row.percentage }}%</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('conditions')" label="条件" width="96">
          <template #default="{ row }">
            <ElButton v-if="row.conditions" link type="primary" @click="openConditions(row)">
              查看
            </ElButton>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('description')"
          prop="description"
          label="描述"
          min-width="180"
          show-overflow-tooltip
        />
        <ElTableColumn label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canEdit" label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <ElSpace>
              <ElButton
                v-permission="PERMISSION.featureFlagEdit"
                link
                type="primary"
                @click="openEdit(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-if="!row.enabled"
                v-permission="PERMISSION.featureFlagEdit"
                link
                type="success"
                @click="onEnable(row)"
              >
                启用
              </ElButton>
              <ElButton
                v-else
                v-permission="PERMISSION.featureFlagEdit"
                link
                type="danger"
                @click="onDisable(row)"
              >
                禁用
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建功能开关' : '编辑功能开关'"
      :confirm-loading="submitting"
      width="600px"
      @confirm="submit"
    >
      <BaseForm
        ref="formRef"
        :model="formModel"
        :rules="rules"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('flag_key')" label="开关标识" prop="flag_key">
          <ElInput
            v-model="formModel.flag_key"
            :disabled="editingId !== null || fields.isReadOnly('flag_key')"
            placeholder="例如 new_homepage"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('flag_name')" label="开关名称" prop="flag_name">
          <ElInput v-model="formModel.flag_name" :disabled="fields.isReadOnly('flag_name')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('enabled')" label="启用状态">
          <ElSwitch v-model="formModel.enabled" :disabled="fields.isReadOnly('enabled')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('strategy')" label="灰度策略">
          <ElSelect v-model="formModel.strategy" :disabled="fields.isReadOnly('strategy')">
            <ElOption
              v-for="item in FEATURE_FLAG_STRATEGY"
              :key="item"
              :label="FEATURE_FLAG_STRATEGY_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('percentage')" label="百分比">
          <ElInputNumber
            v-model="formModel.percentage"
            :min="0"
            :max="100"
            :disabled="fields.isReadOnly('percentage')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('conditions')" label="条件 (JSON)">
          <ElInput
            v-model="conditionsText"
            type="textarea"
            :rows="4"
            :disabled="fields.isReadOnly('conditions')"
            placeholder='例如 {"min_level": 5}'
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="formModel.description"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <BaseDialog v-model="conditionsVisible" title="开关条件" width="560px" hide-footer>
      <DataStateView
        :loading="false"
        :failed="false"
        :empty="activeConditions === null"
        empty-text="该开关没有配置条件"
      >
        <JsonViewer :value="activeConditions" />
      </DataStateView>
    </BaseDialog>
  </div>
</template>

<style scoped>
.feature-flag-page__filters {
  margin-bottom: 16px;
}
</style>
