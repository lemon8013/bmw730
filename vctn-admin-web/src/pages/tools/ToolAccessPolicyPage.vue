<script setup lang="ts">
/** 工具访问策略：编辑各工具对 GUEST / USER 的访问配额。 */
import { computed, reactive, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElFormItem,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'

import { listAdminAccessPolicies, upsertAdminAccessPolicy } from '@/api/tools'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type { AccessPolicyRequest, AdminAccessPolicy } from '@/types/tools'
import { TOOL_SUBJECT_TYPE, TOOL_SUBJECT_TYPE_LABEL } from '@/types/enums'
import { renderError, type RenderedError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolAccessManage)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toPolicy(row: Record<string, unknown>): AdminAccessPolicy {
  return row as unknown as AdminAccessPolicy
}

/** 空配额表示“不限”。 */
function limitText(value: unknown): string {
  return typeof value === 'number' ? String(value) : '不限'
}

function policyToolId(policy: AdminAccessPolicy): string {
  return policy.tool_id === null || policy.tool_id === undefined ? '' : String(policy.tool_id)
}

// ---------------------------------------------------------------------------
// 列表
// ---------------------------------------------------------------------------

const { data, loading, failed, error, reload } = useAsyncData(() => listAdminAccessPolicies())

const rows = computed(() => asRows(data.value ?? []))

// ---------------------------------------------------------------------------
// 编辑
// ---------------------------------------------------------------------------

type PolicyFormModel = {
  subject_type: string
  enabled: boolean
  daily_limit: number | undefined
  rate_limit_per_minute: number | undefined
  concurrency_limit: number | undefined
}

const editModel = reactive<PolicyFormModel>({
  subject_type: 'USER',
  enabled: true,
  daily_limit: undefined,
  rate_limit_per_minute: undefined,
  concurrency_limit: undefined,
})

const editVisible = ref(false)
const editSubmitting = ref(false)
const activePolicy = ref<AdminAccessPolicy | null>(null)
const dialogError = ref<RenderedError | null>(null)

function toMessages(): { message: string | null; traceId: string | null } {
  return {
    message: dialogError.value?.message ?? null,
    traceId: dialogError.value?.traceId ?? null,
  }
}

function openEdit(row: Record<string, unknown>): void {
  const policy = toPolicy(row)
  activePolicy.value = policy
  Object.assign(editModel, {
    subject_type: policy.subject_type,
    enabled: policy.enabled,
    daily_limit: policy.daily_limit ?? undefined,
    rate_limit_per_minute: policy.rate_limit_per_minute ?? undefined,
    concurrency_limit: policy.concurrency_limit ?? undefined,
  })
  dialogError.value = null
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  const policy = activePolicy.value
  if (policy === null) {
    return
  }
  const toolId = policyToolId(policy)
  if (toolId === '') {
    dialogError.value = renderError(new Error('该策略缺少工具 ID，无法保存'))
    return
  }
  dialogError.value = null
  editSubmitting.value = true
  try {
    const payload: AccessPolicyRequest = {
      subject_type: editModel.subject_type,
      enabled: editModel.enabled,
      daily_limit: editModel.daily_limit ?? null,
      rate_limit_per_minute: editModel.rate_limit_per_minute ?? null,
      concurrency_limit: editModel.concurrency_limit ?? null,
    }
    await upsertAdminAccessPolicy(toolId, payload)
    notify.success('访问策略已保存')
    editVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    editSubmitting.value = false
  }
}
</script>

<template>
  <div class="tool-access-page">
    <PageHeader title="工具访问策略" description="配置每个工具对不同主体类型的启用状态与调用配额。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="tool-access-page__notice"
      title="关于运行时用量"
      description="本页数据来自管理端接口 /admin/tools/access-policies，仅包含策略配置。运行时用量（used_today / remaining）由用户侧访问接口提供，属于管理端不可见的运行时视图，因此本页不查询用量接口。空配额字段表示“不限（null）”。"
    />

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
        empty-text="暂无访问策略"
        @retry="reload"
      >
        <ElTableColumn v-if="!fields.isHidden('tool_name')" label="工具" min-width="180">
          <template #default="{ row }">
            {{ row.tool_name ?? row.tool_id ?? '—' }}
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('subject_type')"
          prop="subject_type"
          label="主体类型"
          width="120"
        >
          <template #default="{ row }">
            <StatusTag :value="row.subject_type" :labels="TOOL_SUBJECT_TYPE_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('enabled')" prop="enabled" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.enabled" :boolean-labels="['禁用', '启用']" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('daily_limit')" label="每日上限" width="120">
          <template #default="{ row }">{{ limitText(row.daily_limit) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('rate_limit_per_minute')"
          label="每分钟限流"
          width="130"
        >
          <template #default="{ row }">{{ limitText(row.rate_limit_per_minute) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('concurrency_limit')"
          label="并发上限"
          width="120"
        >
          <template #default="{ row }">{{ limitText(row.concurrency_limit) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('updated_at')" label="更新时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <ElButton
              v-permission="PERMISSION.toolAccessEdit"
              link
              type="primary"
              :disabled="!row.tool_id"
              @click="openEdit(row)"
            >
              编辑
            </ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="editVisible"
      :title="activePolicy?.tool_name ? `编辑访问策略：${activePolicy.tool_name}` : '编辑访问策略'"
      width="640px"
      :confirm-loading="editSubmitting"
      @confirm="submitEdit"
    >
      <BaseForm
        :model="editModel"
        :error-message="toMessages().message"
        :error-trace-id="toMessages().traceId"
        label-width="140px"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('subject_type')" label="主体类型">
          <ElSelect
            v-model="editModel.subject_type"
            :disabled="fields.isReadOnly('subject_type')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in TOOL_SUBJECT_TYPE"
              :key="item"
              :label="TOOL_SUBJECT_TYPE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('enabled')" label="启用">
          <ElSwitch v-model="editModel.enabled" :disabled="fields.isReadOnly('enabled')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('daily_limit')" label="每日上限">
          <ElInputNumber
            v-model="editModel.daily_limit"
            :min="1"
            :controls="false"
            placeholder="留空表示不限"
            :disabled="fields.isReadOnly('daily_limit')"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('rate_limit_per_minute')" label="每分钟限流">
          <ElInputNumber
            v-model="editModel.rate_limit_per_minute"
            :min="1"
            :controls="false"
            placeholder="留空表示不限"
            :disabled="fields.isReadOnly('rate_limit_per_minute')"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('concurrency_limit')" label="并发上限">
          <ElInputNumber
            v-model="editModel.concurrency_limit"
            :min="1"
            :controls="false"
            placeholder="留空表示不限"
            :disabled="fields.isReadOnly('concurrency_limit')"
            style="width: 100%"
          />
        </ElFormItem>
        <p class="tool-access-page__hint">
          以上配额字段留空即表示不限（提交为 null）；填入正整数则按该值限制调用。
        </p>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.tool-access-page__notice {
  margin-bottom: 16px;
}

.tool-access-page__hint {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
