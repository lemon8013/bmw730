<script setup lang="ts">
/** 积分：只读查看积分规则。 */
import { computed } from 'vue'
import { ElCard, ElTableColumn } from 'element-plus'

import { listPointRules } from '@/api/points'
import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { formatNumber } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.pointRuleView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

// ---------------------------------------------------------------------------
// 积分规则（公开端点，管理员身份可读）
// ---------------------------------------------------------------------------

const {
  data: ruleData,
  loading: rulesLoading,
  failed: rulesFailed,
  error: rulesError,
  reload: reloadRules,
} = useAsyncData(() => listPointRules())

const ruleRows = computed(() => asRows(ruleData.value ?? []))
</script>

<template>
  <div class="point-page">
    <PageHeader title="积分" description="查看积分规则；积分账户与流水按业务用户取数。" />

    <BizIdentityNotice subject="积分账户与流水" />

    <ElCard shadow="never">
      <template #header>积分规则</template>
      <BaseTable
        :rows="ruleRows"
        :loading="rulesLoading"
        :failed="rulesFailed"
        :error="rulesError"
        :total="0"
        :page="1"
        :page-size="1"
        :paginated="false"
        row-key="rule_code"
        empty-text="暂无积分规则"
        @retry="reloadRules"
      >
        <ElTableColumn v-if="!fields.isHidden('rule_code')" prop="rule_code" label="规则编码" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('rule_name')" prop="rule_name" label="规则名称" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('event_code')" prop="event_code" label="事件编码" min-width="160" />
        <ElTableColumn v-if="!fields.isHidden('points')" prop="points" label="积分" width="100" />
        <ElTableColumn v-if="!fields.isHidden('daily_limit')" label="每日上限" width="110">
          <template #default="{ row }">{{ formatNumber(row.daily_limit) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('cooldown_seconds')" label="冷却(秒)" width="110">
          <template #default="{ row }">{{ formatNumber(row.cooldown_seconds) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('enabled')"
          prop="enabled"
          label="启用"
          width="90"
        >
          <template #default="{ row }">
            <StatusTag :value="row.enabled" :boolean-labels="['禁用', '启用']" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('description')" prop="description" label="描述" min-width="180" show-overflow-tooltip />
      </BaseTable>
    </ElCard>
  </div>
</template>

<style scoped>
.point-page__section {
  margin-bottom: 16px;
}
</style>
