<script setup lang="ts">
/**
 * 成就：成就目录 + 按业务用户查看已解锁情况。
 *
 * 平台侧的 `/achievements/me` 按登录的业务用户取数，管理员调用一律 401。本页
 * 改走 `/admin/users/{id}/achievements`，后端把「全部成就」与「该用户是否已解
 * 锁」合并返回，因此一次请求就能渲染出完整的达成矩阵。
 */
import { computed, ref } from 'vue'
import { ElButton, ElCard, ElTableColumn } from 'element-plus'

import { getUserAchievements } from '@/api/growth'
import BizUserPicker from '@/components/growth/BizUserPicker.vue'
import JsonViewer from '@/components/common/JsonViewer.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'

const fields = useFieldPolicy(PERMISSION.achievementConfigView)

const MAX_PAGE_SIZE = 200

const selectedUserId = ref('')

const {
  data: achievements,
  loading,
  failed,
  error,
  reload,
} = useAsyncData(() => getUserAchievements(selectedUserId.value), { immediate: false })

const rows = computed(() => (achievements.value ?? []) as unknown as Record<string, unknown>[])

async function onUserChange(user: { user_id: string } | null): Promise<void> {
  const userId = user?.user_id ?? ''
  selectedUserId.value = userId
  if (userId) {
    await reload()
  }
}

const unlockedCount = computed(
  () => rows.value.filter((row) => row.unlocked === true).length,
)

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
    <PageHeader title="成就" description="成就目录，以及按业务用户查看的解锁情况。">
      <template #actions>
        <ElButton v-if="selectedUserId" @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="achievement-page__section">
      <template #header>
        <div class="achievement-page__header">
          <span>
            成就达成情况
            <template v-if="selectedUserId">
              （已解锁 {{ unlockedCount }} / {{ rows.length }}）
            </template>
          </span>
          <BizUserPicker :model-value="selectedUserId" width="320px" @change="onUserChange" />
        </div>
      </template>
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="0"
        :page="1"
        :page-size="MAX_PAGE_SIZE"
        :paginated="false"
        row-key="achievement_code"
        :empty-text="selectedUserId ? '暂无成就' : '请选择业务用户'"
        @retry="reload"
      >
        <ElTableColumn
          v-if="!fields.isHidden('achievement_code')"
          prop="achievement_code"
          label="成就编码"
          min-width="180"
        />
        <ElTableColumn
          v-if="!fields.isHidden('achievement_name')"
          prop="achievement_name"
          label="成就名称"
          min-width="150"
        />
        <ElTableColumn label="解锁状态" width="120">
          <template #default="{ row }">
            <StatusTag :value="row.unlocked" :boolean-labels="['未解锁', '已解锁']" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="achieved_at" label="解锁时间" min-width="180" />
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

    <BaseDialog v-model="jsonVisible" :title="jsonTitle" width="560px" hide-footer>
      <JsonViewer :value="jsonValue" />
    </BaseDialog>
  </div>
</template>

<style scoped>
.achievement-page__section {
  margin-bottom: 16px;
}

.achievement-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
