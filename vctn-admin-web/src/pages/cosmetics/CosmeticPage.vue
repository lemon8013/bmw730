<script setup lang="ts">
/**
 * 装扮：装扮目录 + 按业务用户查看持有与装备情况。
 *
 * 平台侧的 `/cosmetics/me` 按登录的业务用户取数，管理员调用一律 401。本页改走
 * `/admin/users/{id}/cosmetics`，后端把「全部装扮」与「该用户是否持有」合并
 * 返回，装备情况另取 `.../cosmetics/equipment`。
 *
 * 装扮的增删改与发放仍无写接口（矩阵里只有 COSMETIC_VIEW / COSMETIC_EDIT 两个
 * 码，本轮未新增发放端点），因此本页保持只读。
 */
import { computed, ref } from 'vue'
import { ElButton, ElCard, ElOption, ElSelect, ElSpace, ElTableColumn } from 'element-plus'

import { getUserCosmetics, getUserEquipment } from '@/api/growth'
import BizUserPicker from '@/components/growth/BizUserPicker.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { COSMETIC_TYPE, COSMETIC_TYPE_LABEL } from '@/types/enums'

const fields = useFieldPolicy(PERMISSION.cosmeticView)

const MAX_PAGE_SIZE = 200

const selectedUserId = ref('')
const selectedType = ref<string>('')

const {
  data: cosmetics,
  loading,
  failed,
  error,
  reload,
} = useAsyncData(() => getUserCosmetics(selectedUserId.value), { immediate: false })

const {
  data: equipment,
  reload: reloadEquipment,
} = useAsyncData(() => getUserEquipment(selectedUserId.value), { immediate: false })

const rows = computed(() => {
  const type = selectedType.value
  const items = cosmetics.value ?? []
  const filtered = type === '' ? items : items.filter((item) => item.cosmetic_type === type)
  return filtered as unknown as Record<string, unknown>[]
})

async function onUserChange(user: { user_id: string } | null): Promise<void> {
  const userId = user?.user_id ?? ''
  selectedUserId.value = userId
  if (userId) {
    await Promise.all([reload(), reloadEquipment()])
  }
}

const ownedCount = computed(() => rows.value.filter((row) => row.owned === true).length)

/** 当前装备的六个槽位，值为 null 表示未装备。 */
const equippedSlots = computed(() => {
  if (!equipment.value) {
    return [] as { label: string; value: string }[]
  }
  const pairs: [string, string][] = [
    ['头像', 'avatar_cosmetic_name'],
    ['头像框', 'avatar_frame_cosmetic_name'],
    ['皇冠', 'crown_cosmetic_name'],
    ['徽章', 'badge_cosmetic_name'],
    ['称号', 'title_cosmetic_name'],
    ['昵称特效', 'name_effect_cosmetic_name'],
  ]
  return pairs.map(([label, key]) => ({
    label,
    value: (equipment.value?.[key] as string | null | undefined) ?? '未装备',
  }))
})

function resetFilters(): void {
  selectedType.value = ''
}
</script>

<template>
  <div class="cosmetic-page">
    <PageHeader title="装扮" description="装扮目录，以及按业务用户查看的持有与装备情况。" />

    <ElCard shadow="never" class="cosmetic-page__filters">
      <ElSpace wrap>
        <BizUserPicker :model-value="selectedUserId" width="280px" @change="onUserChange" />
        <ElSelect
          v-model="selectedType"
          placeholder="按装扮类型筛选"
          clearable
          style="width: 200px"
        >
          <ElOption
            v-for="item in COSMETIC_TYPE"
            :key="item"
            :label="COSMETIC_TYPE_LABEL[item] ?? item"
            :value="item"
          />
        </ElSelect>
        <ElButton @click="resetFilters">重置筛选</ElButton>
        <ElButton v-if="selectedUserId" @click="reload">刷新</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard v-if="selectedUserId" shadow="never" class="cosmetic-page__section">
      <template #header>当前装备</template>
      <ElSpace wrap>
        <span v-for="slot in equippedSlots" :key="slot.label" class="cosmetic-page__slot">
          <span class="cosmetic-page__slot-label">{{ slot.label }}</span>
          <span>{{ slot.value }}</span>
        </span>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never" class="cosmetic-page__section">
      <template #header>
        <div class="cosmetic-page__header">
          <span>
            装扮目录
            <template v-if="selectedUserId">（已持有 {{ ownedCount }} / {{ rows.length }}）</template>
          </span>
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
        row-key="cosmetic_code"
        :empty-text="selectedUserId ? '暂无装扮' : '请选择业务用户'"
        @retry="reload"
      >
        <ElTableColumn
          v-if="!fields.isHidden('cosmetic_code')"
          prop="cosmetic_code"
          label="装扮编码"
          min-width="180"
        />
        <ElTableColumn
          v-if="!fields.isHidden('cosmetic_name')"
          prop="cosmetic_name"
          label="装扮名称"
          min-width="150"
        />
        <ElTableColumn
          v-if="!fields.isHidden('cosmetic_type')"
          prop="cosmetic_type"
          label="装扮类型"
          width="140"
        >
          <template #default="{ row }">
            <StatusTag :value="row.cosmetic_type" :labels="COSMETIC_TYPE_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('sort_order')" prop="sort_order" label="排序" width="90" />
        <ElTableColumn label="持有状态" width="120">
          <template #default="{ row }">
            <StatusTag :value="row.owned" :boolean-labels="['未持有', '已持有']" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="obtained_at" label="获得时间" min-width="180" />
        <ElTableColumn prop="source_type" label="来源" width="120" />
        <ElTableColumn
          v-if="!fields.isHidden('asset_url')"
          prop="asset_url"
          label="资源地址"
          min-width="200"
          show-overflow-tooltip
        />
      </BaseTable>
    </ElCard>
  </div>
</template>

<style scoped>
.cosmetic-page__filters {
  margin-bottom: 16px;
}

.cosmetic-page__section {
  margin-bottom: 16px;
}

.cosmetic-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cosmetic-page__slot {
  padding: 6px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  font-size: 13px;
}

.cosmetic-page__slot-label {
  margin-right: 8px;
  color: var(--el-text-color-secondary);
}
</style>
