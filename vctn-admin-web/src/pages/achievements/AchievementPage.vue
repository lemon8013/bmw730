<script setup lang="ts">
/** 成就：只读查看成就目录与当前身份已获得的成就。 */
import { computed, ref } from 'vue'
import { ElAlert, ElButton, ElCard, ElTableColumn } from 'element-plus'

import { listAchievements } from '@/api/achievements'
import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PAGE_PERMISSION } from '@/constants/permissions'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PAGE_PERMISSION.achievement)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

// ---------------------------------------------------------------------------
// 成就目录
// ---------------------------------------------------------------------------

const {
  data: achievementData,
  loading: achievementsLoading,
  failed: achievementsFailed,
  error: achievementsError,
  reload: reloadAchievements,
} = useAsyncData(() => listAchievements())

const achievementRows = computed(() => asRows(achievementData.value ?? []))

// ---------------------------------------------------------------------------
// 我的成就
//
// `/achievements/me` resolves identity from the signed-in business user, which
// an operator session does not have, so the section renders a notice instead.
// ---------------------------------------------------------------------------

function refreshAll(): void {
  void reloadAchievements()
}

// ---------------------------------------------------------------------------
// JSON 查看
// ---------------------------------------------------------------------------

const jsonVisible = ref(false)
const jsonTitle = ref('')
const jsonValue = ref<unknown>(null)

function openJson(title: string, value: unknown): void {
  jsonTitle.value = title
  jsonValue.value = value ?? null
  jsonVisible.value = true
}
</script>

<template>
  <div class="achievement-page">
    <PageHeader title="成就" description="查看成就目录（只读）。">
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="achievement-page__notice"
      title="成就配置为只读"
      description="后端尚未实现成就的增删改接口，因此本页不提供任何成就维护入口。"
    />

    <ElCard shadow="never" class="achievement-page__section">
      <template #header>成就目录</template>
      <BaseTable
        :rows="achievementRows"
        :loading="achievementsLoading"
        :failed="achievementsFailed"
        :error="achievementsError"
        :total="0"
        :page="1"
        :page-size="1"
        :paginated="false"
        row-key="id"
        empty-text="暂无成就"
        @retry="reloadAchievements"
      >
        <ElTableColumn
          v-if="!fields.isHidden('achievement_code')"
          prop="achievement_code"
          label="成就编码"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('achievement_name')"
          prop="achievement_name"
          label="成就名称"
          min-width="160"
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="110">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('reward')" label="奖励" width="100">
          <template #default="{ row }">
            <ElButton
              v-if="row.reward"
              link
              type="primary"
              @click="openJson('成就奖励', row.reward)"
            >
              查看
            </ElButton>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('conditions')" label="条件" width="100">
          <template #default="{ row }">
            <ElButton
              v-if="row.conditions"
              link
              type="primary"
              @click="openJson('成就条件', row.conditions)"
            >
              查看
            </ElButton>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never">
      <template #header>我的成就</template>
      <BizIdentityNotice subject="已获得的成就" />
    </ElCard>

    <BaseDialog v-model="jsonVisible" :title="jsonTitle" width="560px" hide-footer>
      <JsonViewer :value="jsonValue" />
    </BaseDialog>
  </div>
</template>

<style scoped>
.achievement-page__notice {
  margin-bottom: 16px;
}

.achievement-page__section {
  margin-bottom: 16px;
}
</style>
