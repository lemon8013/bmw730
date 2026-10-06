<script setup lang="ts">
/**
 * 积分：规则配置 + 按业务用户查看账户 / 流水 / 手动调整。
 *
 * 平台侧的 `/points/me` 按登录的业务用户取数，管理员调用一律 401，本页改走
 * `/admin/points/rules` 与 `/admin/users/{id}/points*`。积分写入仍由后端
 * PointService 记账（行锁 + 版本推进 + 不允许透支），这里只提供入口。
 */
import { computed, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSwitch,
  ElTableColumn,
} from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import {
  adjustUserPoints,
  createPointRule,
  deletePointRule,
  getGrowthOverview,
  getUserPointTransactions,
  getUserPoints,
  listAdminPointRules,
  updatePointRule,
} from '@/api/growth'
import BizUserPicker from '@/components/growth/BizUserPicker.vue'
import StatCard from '@/components/charts/StatCard.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type { PointRule, PointRuleCreatePayload, PointRuleUpdatePayload } from '@/types/growth'
import { renderError } from '@/utils/error'
import { formatNumber } from '@/utils/format'

/** 失败提示统一取服务端 message，拿不到时退回通用文案。 */
function failureText(caught: unknown): string {
  return renderError(caught).message
}

const notify = useConfirm()
const fields = useFieldPolicy(PERMISSION.pointRuleView)
const permission = usePermissionStore()

const canEditRules = computed(() => permission.has(PERMISSION.pointRuleEdit))
const canAdjust = computed(() => permission.has(PERMISSION.userPointAdjust))

const MAX_PAGE_SIZE = 200

// ---------------------------------------------------------------------------
// 概览
// ---------------------------------------------------------------------------

const { data: overview, reload: reloadOverview } = useAsyncData(() => getGrowthOverview())

// ---------------------------------------------------------------------------
// 积分规则
// ---------------------------------------------------------------------------

const {
  data: rules,
  loading: rulesLoading,
  failed: rulesFailed,
  error: rulesError,
  reload: reloadRules,
} = useAsyncData(() => listAdminPointRules(true))

const ruleRows = computed(
  () => (rules.value ?? []) as unknown as Record<string, unknown>[],
)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()

interface RuleForm {
  rule_code: string
  rule_name: string
  event_code: string
  points: number
  daily_limit: number | null
  cooldown_seconds: number | null
  enabled: boolean
  description: string
}

function emptyForm(): RuleForm {
  return {
    rule_code: '',
    rule_name: '',
    event_code: '',
    points: 0,
    daily_limit: null,
    cooldown_seconds: null,
    enabled: true,
    description: '',
  }
}

const form = reactive<RuleForm>(emptyForm())

const formRules: FormRules<RuleForm> = {
  rule_code: [{ required: true, message: '请填写规则编码', trigger: 'blur' }],
  rule_name: [{ required: true, message: '请填写规则名称', trigger: 'blur' }],
  event_code: [{ required: true, message: '请填写事件编码', trigger: 'blur' }],
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const rule = row as unknown as PointRule
  editingId.value = rule.id
  Object.assign(form, {
    rule_code: rule.rule_code,
    rule_name: rule.rule_name,
    event_code: rule.event_code,
    points: rule.points,
    daily_limit: rule.daily_limit ?? null,
    cooldown_seconds: rule.cooldown_seconds ?? null,
    enabled: rule.enabled,
    description: rule.description ?? '',
  })
  dialogVisible.value = true
}

async function submitRule(): Promise<void> {
  if (!formRef.value) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    if (editingId.value === null) {
      const payload: PointRuleCreatePayload = {
        rule_code: form.rule_code,
        rule_name: form.rule_name,
        event_code: form.event_code,
        points: form.points,
        daily_limit: form.daily_limit,
        cooldown_seconds: form.cooldown_seconds,
        enabled: form.enabled,
        description: form.description || null,
      }
      await createPointRule(payload)
      notify.success('已新增积分规则')
    } else {
      const payload: PointRuleUpdatePayload = {
        rule_name: form.rule_name,
        points: form.points,
        daily_limit: form.daily_limit,
        cooldown_seconds: form.cooldown_seconds,
        enabled: form.enabled,
        description: form.description || null,
      }
      await updatePointRule(editingId.value, payload)
      notify.success('已更新积分规则')
    }
    dialogVisible.value = false
    await reloadRules()
    await reloadOverview()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    submitting.value = false
  }
}

async function removeRule(row: Record<string, unknown>): Promise<void> {
  const rule = row as unknown as PointRule
  const confirmed = await notify.confirm({
    title: '停用积分规则',
    message: `停用「${rule.rule_name}」后，${rule.event_code} 事件不再自动加积分。已产生的流水不受影响。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deletePointRule(rule.id)
    notify.success('已停用积分规则')
    await reloadRules()
    await reloadOverview()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 用户积分账户与流水
// ---------------------------------------------------------------------------

const selectedUserId = ref('')
const page = ref(1)
const pageSize = ref(20)

const {
  data: account,
  loading: accountLoading,
  failed: accountFailed,
  error: accountError,
  reload: reloadAccount,
} = useAsyncData(() => getUserPoints(selectedUserId.value), { immediate: false })

const {
  data: transactions,
  loading: txLoading,
  failed: txFailed,
  error: txError,
  reload: reloadTx,
} = useAsyncData(
  () =>
    getUserPointTransactions(selectedUserId.value, {
      page: page.value,
      page_size: pageSize.value,
    }),
  { immediate: false },
)

const txRows = computed(
  () => (transactions.value?.items ?? []) as unknown as Record<string, unknown>[],
)

async function onUserChange(user: { user_id: string } | null): Promise<void> {
  const userId = user?.user_id ?? ''
  selectedUserId.value = userId
  if (!userId) {
    return
  }
  page.value = 1
  await Promise.all([reloadAccount(), reloadTx()])
}

// ---------------------------------------------------------------------------
// 手动调整
// ---------------------------------------------------------------------------

const adjustVisible = ref(false)
const adjustSubmitting = ref(false)
const adjust = reactive({ delta_points: 100, reason: '' })

function openAdjust(): void {
  adjust.delta_points = 100
  adjust.reason = ''
  adjustVisible.value = true
}

async function submitAdjust(): Promise<void> {
  if (adjust.delta_points === 0) {
    notify.failure('调整量不能为 0')
    return
  }
  adjustSubmitting.value = true
  try {
    const result = await adjustUserPoints(selectedUserId.value, {
      delta_points: adjust.delta_points,
      reason: adjust.reason || 'ADMIN_ADJUSTMENT',
    })
    notify.success(`已调整为 ${result.balance}`)
    adjustVisible.value = false
    await reloadAccount()
    await reloadTx()
    await reloadOverview()
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    adjustSubmitting.value = false
  }
}

function refreshAll(): void {
  void reloadRules()
  void reloadOverview()
  if (selectedUserId.value) {
    void reloadAccount()
    void reloadTx()
  }
}
</script>

<template>
  <div class="point-page">
    <PageHeader
      title="积分"
      description="积分规则配置，以及按业务用户查看的积分账户、流水与手动调整。"
    >
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <div class="point-page__stats">
      <StatCard label="积分账户" :value="formatNumber(overview?.point_account_count ?? 0)" />
      <StatCard label="流通余额" :value="formatNumber(overview?.total_point_balance ?? 0)" />
      <StatCard
        label="启用规则"
        :value="`${overview?.point_rule_enabled ?? 0} / ${overview?.point_rule_count ?? 0}`"
      />
      <StatCard
        label="已领任务奖励"
        :value="formatNumber(overview?.user_task_reward_claimed ?? 0)"
      />
    </div>

    <ElCard shadow="never" class="point-page__section">
      <template #header>
        <div class="point-page__header">
          <span>积分规则</span>
          <ElButton v-if="canEditRules" type="primary" @click="openCreate">新增规则</ElButton>
        </div>
      </template>
      <BaseTable
        :rows="ruleRows"
        :loading="rulesLoading"
        :failed="rulesFailed"
        :error="rulesError"
        :total="0"
        :page="1"
        :page-size="MAX_PAGE_SIZE"
        :paginated="false"
        row-key="rule_code"
        empty-text="暂无积分规则"
        @retry="reloadRules"
      >
        <ElTableColumn
          v-if="!fields.isHidden('rule_code')"
          prop="rule_code"
          label="规则编码"
          min-width="200"
        />
        <ElTableColumn
          v-if="!fields.isHidden('rule_name')"
          prop="rule_name"
          label="规则名称"
          min-width="130"
        />
        <ElTableColumn
          v-if="!fields.isHidden('event_code')"
          prop="event_code"
          label="事件编码"
          min-width="180"
        />
        <ElTableColumn v-if="!fields.isHidden('points')" prop="points" label="积分" width="100" />
        <ElTableColumn v-if="!fields.isHidden('daily_limit')" label="每日上限" width="110">
          <template #default="{ row }">{{ row.daily_limit ?? '不限' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('cooldown_seconds')" label="冷却(秒)" width="110">
          <template #default="{ row }">{{ row.cooldown_seconds ?? '不限' }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('enabled')" prop="enabled" label="启用" width="90">
          <template #default="{ row }">
            <StatusTag :value="row.enabled" :boolean-labels="['禁用', '启用']" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openEdit(row)">
              {{ canEditRules ? '编辑' : '查看' }}
            </ElButton>
            <ElButton v-if="canEditRules" link type="danger" @click="removeRule(row)">
              停用
            </ElButton>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never" class="point-page__section">
      <template #header>
        <div class="point-page__header">
          <span>用户积分账户</span>
          <BizUserPicker :model-value="selectedUserId" width="320px" @change="onUserChange" />
        </div>
      </template>

      <DataStateView
        :loading="accountLoading"
        :failed="accountFailed"
        :error="accountError"
        :empty="!selectedUserId || !account"
        empty-text="请选择业务用户"
        @retry="reloadAccount"
      >
        <template v-if="account">
          <div class="point-page__stats">
            <StatCard label="当前余额" :value="formatNumber(account.balance)" />
            <StatCard label="累计获得" :value="formatNumber(account.total_earned)" />
            <StatCard label="累计消耗" :value="formatNumber(account.total_spent)" />
            <StatCard label="版本号" :value="formatNumber(account.version)" />
          </div>

          <ElButton v-if="canAdjust" type="primary" @click="openAdjust">调整积分</ElButton>
        </template>
      </DataStateView>
    </ElCard>

    <ElCard v-if="selectedUserId" shadow="never" class="point-page__section">
      <template #header>积分流水</template>
      <BaseTable
        :rows="txRows"
        :loading="txLoading"
        :failed="txFailed"
        :error="txError"
        :total="transactions?.total ?? 0"
        :page="page"
        :page-size="pageSize"
        :paginated="true"
        row-key="id"
        empty-text="暂无积分流水"
        @retry="reloadTx"
        @update:page="(p: number) => { page = p; void reloadTx() }"
        @update:page-size="(s: number) => { pageSize = s; page = 1; void reloadTx() }"
      >
        <ElTableColumn prop="id" label="流水号" min-width="180" />
        <ElTableColumn prop="delta_points" label="变动" width="100">
          <template #default="{ row }">
            <span :class="row.delta_points >= 0 ? 'point-page__plus' : 'point-page__minus'">
              {{ row.delta_points >= 0 ? '+' : '' }}{{ row.delta_points }}
            </span>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="balance_after" label="变动后" width="110" />
        <ElTableColumn prop="transaction_type" label="类型" width="110" />
        <ElTableColumn prop="source_type" label="来源" width="110" />
        <ElTableColumn prop="reason" label="原因" min-width="160" show-overflow-tooltip />
        <ElTableColumn prop="created_at" label="时间" min-width="180" />
      </BaseTable>
    </ElCard>

    <ElDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增积分规则' : '编辑积分规则'"
      width="520px"
    >
      <ElForm ref="formRef" :model="form" :rules="formRules" label-width="110px">
        <ElFormItem label="规则编码" prop="rule_code">
          <ElInput
            v-model="form.rule_code"
            :disabled="editingId !== null"
            placeholder="POINT_XXX"
          />
        </ElFormItem>
        <ElFormItem label="规则名称" prop="rule_name">
          <ElInput v-model="form.rule_name" />
        </ElFormItem>
        <ElFormItem label="事件编码" prop="event_code">
          <ElInput v-model="form.event_code" placeholder="TOOL_EXECUTION_SUCCESS" />
        </ElFormItem>
        <ElFormItem label="积分">
          <ElInputNumber v-model="form.points" />
        </ElFormItem>
        <ElFormItem label="每日上限">
          <ElInputNumber v-model="form.daily_limit" :min="0" />
        </ElFormItem>
        <ElFormItem label="冷却(秒)">
          <ElInputNumber v-model="form.cooldown_seconds" :min="0" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="form.description" type="textarea" :rows="2" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitRule">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="adjustVisible" title="调整积分" width="460px">
      <ElForm label-width="110px">
        <ElFormItem label="增量">
          <ElInputNumber v-model="adjust.delta_points" />
        </ElFormItem>
        <ElFormItem label="原因">
          <ElInput
            v-model="adjust.reason"
            type="textarea"
            :rows="2"
            placeholder="会写入流水与审计日志"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="adjustVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="adjustSubmitting" @click="submitAdjust">
          确定
        </ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.point-page__section {
  margin-top: 16px;
}

.point-page__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.point-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.point-page__plus {
  color: var(--vctn-success);
}

.point-page__minus {
  color: var(--vctn-danger);
}
</style>
