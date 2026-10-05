<script setup lang="ts">
/** Popularity ranking over a rolling window. */
import { computed, ref } from 'vue'
import { ElCard, ElOption, ElSelect } from 'element-plus'

import { popularTools } from '@/api/tools'
import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AsyncSection from '@/components/AsyncSection.vue'
import ToolCard from '@/components/ToolCard.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { PopularToolItem, ToolCatalogItem } from '@/types/catalog'

const windowDays = ref(7)

const state = useAsyncData<PopularToolItem[]>(() => popularTools(windowDays.value, 50))

async function onWindowChange(): Promise<void> {
  windowDays.value = Number(windowDays.value)
  await state.reload()
}

const rows = computed(() => state.data.value ?? [])

/** Popular rows only carry tool_id/name/slug; adapt them to the card shape. */
function popularAsTool(item: PopularToolItem): ToolCatalogItem {
  return {
    id: item.tool_id,
    code: item.tool_slug ?? item.tool_id,
    name: item.tool_name ?? item.tool_id,
    slug: item.tool_slug ?? item.tool_id,
    category_id: null,
    icon: null,
    summary: null,
    description: null,
    keywords: [],
    tags: [],
    component_key: '',
    execution_mode: 'BACKEND',
    status: 'ACTIVE',
    sort_order: 0,
    current_version_id: null,
  }
}
</script>

<template>
  <div class="popular-page">
    <AppBreadcrumb :entries="[{ label: '热门工具' }]" />

    <ElCard shadow="never" class="popular-page__head">
      <div class="popular-page__head-inner">
        <h1 class="popular-page__title">热门工具</h1>
        <ElSelect v-model="windowDays" style="width: 140px" @change="onWindowChange">
          <ElOption :value="1" label="最近 1 天" />
          <ElOption :value="7" label="最近 7 天" />
          <ElOption :value="30" label="最近 30 天" />
        </ElSelect>
      </div>
    </ElCard>

    <ElCard shadow="never">
      <AsyncSection
        :loading="state.loading.value"
        :failed="state.failed.value"
        :error="state.error.value"
        :empty="rows.length === 0"
        empty-text="暂无使用数据，用起来的工具会出现在这里"
        @retry="state.reload"
      >
        <div class="popular-page__grid">
          <ToolCard
            v-for="item in rows"
            :key="item.tool_id"
            :tool="popularAsTool(item)"
            :rank="item.rank_no ?? undefined"
            :usage-count="item.usage_count"
          />
        </div>
      </AsyncSection>
    </ElCard>
  </div>
</template>

<style scoped>
.popular-page__head {
  margin-bottom: 16px;
}

.popular-page__head-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.popular-page__title {
  margin: 0;
  font-size: 18px;
}

.popular-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
</style>
