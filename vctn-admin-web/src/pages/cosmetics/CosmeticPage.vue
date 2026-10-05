<script setup lang="ts">
/** 装扮：只读查看装扮目录（按类型筛选）与当前身份已获得的装扮。 */
import { computed, ref } from 'vue'
import { ElAlert, ElButton, ElCard, ElOption, ElSelect, ElSpace, ElTableColumn } from 'element-plus'

import { listCosmetics } from '@/api/cosmetics'
import BizIdentityNotice from '@/components/common/BizIdentityNotice.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import { COSMETIC_TYPE, COSMETIC_TYPE_LABEL } from '@/types/enums'

/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.cosmeticView)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

// ---------------------------------------------------------------------------
// 装扮目录
// ---------------------------------------------------------------------------

const selectedType = ref<string>('')

const {
  data: cosmeticData,
  loading: cosmeticsLoading,
  failed: cosmeticsFailed,
  error: cosmeticsError,
  reload: reloadCosmetics,
} = useAsyncData(() => listCosmetics())

/** 在已加载的行上按装扮类型筛选。 */
const cosmeticRows = computed(() => {
  const type = selectedType.value
  const items = cosmeticData.value ?? []
  const filtered = type === '' ? items : items.filter((item) => item.cosmetic_type === type)
  return asRows(filtered)
})

function resetFilters(): void {
  selectedType.value = ''
  void reloadCosmetics()
}

// ---------------------------------------------------------------------------
// 我的装扮
//
// `/cosmetics/me` resolves identity from the signed-in business user, which an
// operator session does not have, so the section renders a notice instead.
// ---------------------------------------------------------------------------
</script>

<template>
  <div class="cosmetic-page">
    <PageHeader title="装扮" description="查看装扮目录（只读）。" />

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="cosmetic-page__notice"
      title="装扮配置与发放为只读"
      description="后端尚未实现装扮的增删改、发放与回收接口，因此本页不提供任何装扮维护入口。"
    />

    <ElCard shadow="never" class="cosmetic-page__filters">
      <ElSpace wrap>
        <ElSelect
          v-model="selectedType"
          placeholder="按装扮类型筛选"
          clearable
          style="width: 220px"
        >
          <ElOption v-for="item in COSMETIC_TYPE" :key="item" :label="item" :value="item" />
        </ElSelect>
        <ElButton @click="resetFilters">重置</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never" class="cosmetic-page__section">
      <template #header>装扮目录</template>
      <BaseTable
        :rows="cosmeticRows"
        :loading="cosmeticsLoading"
        :failed="cosmeticsFailed"
        :error="cosmeticsError"
        :total="0"
        :page="1"
        :page-size="1"
        :paginated="false"
        row-key="id"
        empty-text="暂无装扮"
        @retry="reloadCosmetics"
      >
        <ElTableColumn v-if="!fields.isHidden('cosmetic_code')" prop="cosmetic_code" label="装扮编码" min-width="150" />
        <ElTableColumn v-if="!fields.isHidden('cosmetic_name')" prop="cosmetic_name" label="装扮名称" min-width="150" />
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
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="110">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="owned" label="是否拥有" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.owned" :boolean-labels="['未拥有', '已拥有']" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('asset_url')"
          prop="asset_url"
          label="资源地址"
          min-width="200"
          show-overflow-tooltip
        />
      </BaseTable>
    </ElCard>

    <ElCard shadow="never">
      <template #header>我的装扮</template>
      <BizIdentityNotice subject="已获得的装扮" />
    </ElCard>
  </div>
</template>

<style scoped>
.cosmetic-page__notice {
  margin-bottom: 16px;
}

.cosmetic-page__filters {
  margin-bottom: 16px;
}

.cosmetic-page__section {
  margin-bottom: 16px;
}
</style>
