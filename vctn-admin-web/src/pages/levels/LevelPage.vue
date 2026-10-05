<script setup lang="ts">
/** 等级：只读查看等级目录、等级详情，以及当前身份所在等级与权益。 */
import { computed, ref } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElRow,
  ElTableColumn,
} from 'element-plus'

import { listLevels } from '@/api/levels'
import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type { UserLevel } from '@/types/growth'
import { formatNumber } from '@/utils/format'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.levelConfigView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

// ---------------------------------------------------------------------------
// 等级目录
// ---------------------------------------------------------------------------

const {
  data: levelData,
  loading: levelsLoading,
  failed: levelsFailed,
  error: levelsError,
  reload: reloadLevels,
} = useAsyncData(() => listLevels())

const levelRows = computed(() => asRows(levelData.value ?? []))

const selectedLevel = ref<UserLevel | null>(null)

function openDetail(row: Record<string, unknown>): void {
  selectedLevel.value = row as unknown as UserLevel
}

// ---------------------------------------------------------------------------
// 我的等级
//
// `/levels/me` resolves identity from the signed-in business user, which an
// operator session does not have, so the section renders a notice instead.
// ---------------------------------------------------------------------------

function refreshAll(): void {
  void reloadLevels()
}
</script>

<template>
  <div class="level-page">
    <PageHeader title="等级" description="查看等级目录与等级详情（只读）。">
      <template #actions>
        <ElButton @click="refreshAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="level-page__notice"
      title="等级配置为只读"
      description="后端尚未实现等级配置的增删改接口（LEVEL_CONFIG_EDIT），因此本页不提供任何等级维护入口。"
    />

    <ElCard shadow="never" class="level-page__mine">
      <template #header>我的等级</template>
      <BizIdentityNotice subject="当前所在等级与权益" />
    </ElCard>

    <ElRow :gutter="16">
      <ElCol :xs="24" :lg="14">
        <ElCard shadow="never">
          <template #header>等级目录</template>
          <BaseTable
            :rows="levelRows"
            :loading="levelsLoading"
            :failed="levelsFailed"
            :error="levelsError"
            :total="0"
            :page="1"
            :page-size="1"
            :paginated="false"
            row-key="id"
            empty-text="暂无等级"
            @retry="reloadLevels"
          >
            <ElTableColumn v-if="!fields.isHidden('level_code')" prop="level_code" label="等级编码" min-width="130" />
            <ElTableColumn v-if="!fields.isHidden('level_name')" prop="level_name" label="等级名称" min-width="130" />
            <ElTableColumn v-if="!fields.isHidden('level_no')" prop="level_no" label="等级序号" width="100" />
            <ElTableColumn label="成长值区间" min-width="160">
              <template #default="{ row }">
                {{ formatNumber(row.min_growth_points) }} ~
                {{ row.max_growth_points === null ? '∞' : formatNumber(row.max_growth_points) }}
              </template>
            </ElTableColumn>
            <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
              <template #default="{ row }">
                <StatusTag :value="row.status" />
              </template>
            </ElTableColumn>
            <ElTableColumn label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <ElButton link type="primary" @click="openDetail(row)">查看</ElButton>
              </template>
            </ElTableColumn>
          </BaseTable>
        </ElCard>
      </ElCol>

      <ElCol :xs="24" :lg="10">
        <ElCard shadow="never">
          <template #header>等级详情</template>
          <DataStateView
            :loading="false"
            :failed="false"
            :empty="selectedLevel === null"
            empty-text="请选择左侧的等级"
          >
            <ElDescriptions v-if="selectedLevel" :column="1" border>
              <ElDescriptionsItem
                v-if="!fields.isHidden('level_code')"
                label="等级编码"
              >
                {{ selectedLevel.level_code }}
              </ElDescriptionsItem>
              <ElDescriptionsItem
                v-if="!fields.isHidden('level_name')"
                label="等级名称"
              >
                {{ selectedLevel.level_name }}
              </ElDescriptionsItem>
              <ElDescriptionsItem v-if="!fields.isHidden('level_no')" label="等级序号">
                {{ selectedLevel.level_no }}
              </ElDescriptionsItem>
              <ElDescriptionsItem label="最小成长值">
                {{ formatNumber(selectedLevel.min_growth_points) }}
              </ElDescriptionsItem>
              <ElDescriptionsItem label="最大成长值">
                {{
                  selectedLevel.max_growth_points === null
                    ? '∞'
                    : formatNumber(selectedLevel.max_growth_points)
                }}
              </ElDescriptionsItem>
              <ElDescriptionsItem v-if="!fields.isHidden('status')" label="状态">
                <StatusTag :value="selectedLevel.status" />
              </ElDescriptionsItem>
              <ElDescriptionsItem
                v-if="!fields.isHidden('description')"
                label="描述"
              >
                {{ selectedLevel.description ?? '—' }}
              </ElDescriptionsItem>
            </ElDescriptions>
          </DataStateView>
        </ElCard>
      </ElCol>
    </ElRow>
  </div>
</template>

<style scoped>
.level-page__notice {
  margin-bottom: 16px;
}

.level-page__mine {
  margin-bottom: 16px;
}
</style>
