<script setup lang="ts">
/** Home: recent usage, popular tools and the catalogue grouped by category. */
import { computed, ref } from 'vue'
import { ElCard } from 'element-plus'

import { listToolCategories, listTools, popularTools } from '@/api/tools'
import AsyncSection from '@/components/AsyncSection.vue'
import ToolCard from '@/components/ToolCard.vue'
import { readRecentSlugs } from '@/composables/recent-tools'
import { useAsyncData } from '@/composables/use-async-data'
import type { PopularToolItem, ToolCatalogItem, ToolCategoryItem } from '@/types/catalog'

const categoriesState = useAsyncData<ToolCategoryItem[]>(() => listToolCategories())
const toolsState = useAsyncData<ToolCatalogItem[]>(() => listTools())
const popularState = useAsyncData<PopularToolItem[]>(() => popularTools(7, 8))

const recentSlugs = ref<string[]>([])

function refreshRecent(): void {
  recentSlugs.value = readRecentSlugs()
}
refreshRecent()

const recentTools = computed<ToolCatalogItem[]>(() => {
  const bySlug = new Map((toolsState.data.value ?? []).map((tool) => [tool.slug, tool]))
  return recentSlugs.value
    .map((slug) => bySlug.get(slug))
    .filter((tool): tool is ToolCatalogItem => tool !== undefined)
    .slice(0, 6)
})

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

function reloadAll(): void {
  void categoriesState.reload()
  void toolsState.reload()
  void popularState.reload()
  refreshRecent()
}

function toolsOf(categoryId: string): ToolCatalogItem[] {
  return (toolsState.data.value ?? []).filter((tool) => tool.category_id === categoryId)
}
</script>

<template>
  <div class="home-page">
    <ElCard shadow="never" class="home-page__hero">
      <h1 class="home-page__title">VCTN Tools</h1>
      <p class="home-page__subtitle">
        在线工具集：数据格式化、编码转换、哈希、正则、ID 生成等
        {{ toolsState.data.value?.length ?? '…' }} 个工具。
      </p>
    </ElCard>

    <ElCard v-if="recentTools.length > 0" shadow="never" class="home-page__section">
      <template #header>最近使用</template>
      <div class="home-page__grid">
        <ToolCard v-for="tool in recentTools" :key="tool.id" :tool="tool" />
      </div>
    </ElCard>

    <ElCard shadow="never" class="home-page__section">
      <template #header>热门工具</template>
      <AsyncSection
        :loading="popularState.loading.value"
        :failed="popularState.failed.value"
        :error="popularState.error.value"
        :empty="(popularState.data.value ?? []).length === 0"
        empty-text="暂无使用数据，用起来的工具会出现在这里"
        @retry="popularState.reload"
      >
        <div class="home-page__grid">
          <ToolCard
            v-for="item in popularState.data.value ?? []"
            :key="item.tool_id"
            :tool="popularAsTool(item)"
            :rank="item.rank_no ?? undefined"
            :usage-count="item.usage_count"
          />
        </div>
      </AsyncSection>
    </ElCard>

    <ElCard
      v-for="category in categoriesState.data.value ?? []"
      :key="category.id"
      shadow="never"
      class="home-page__section"
    >
      <template #header>
        <div class="home-page__category-head">
          <span>{{ category.category_name }}</span>
          <RouterLink
            :to="{ name: 'category', params: { slug: category.category_code } }"
            class="home-page__more"
          >
            查看全部 →
          </RouterLink>
        </div>
      </template>
      <AsyncSection
        :loading="toolsState.loading.value"
        :failed="toolsState.failed.value"
        :error="toolsState.error.value"
        :empty="toolsOf(category.id).length === 0"
        empty-text="该分类下暂无工具"
        @retry="reloadAll"
      >
        <div class="home-page__grid">
          <ToolCard v-for="tool in toolsOf(category.id)" :key="tool.id" :tool="tool" />
        </div>
      </AsyncSection>
    </ElCard>
  </div>
</template>

<style scoped>
.home-page__hero {
  padding-bottom: var(--vctn-space-4);
  margin-bottom: var(--vctn-space-5);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.home-page__title {
  margin: 0 0 var(--vctn-space-2);
  color: var(--vctn-text-strong);
  font-size: 26px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.home-page__subtitle {
  margin: 0;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
}

.home-page__section {
  margin-bottom: var(--vctn-space-6);
}

.home-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--vctn-space-3);
}

.home-page__category-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--vctn-space-3);
}

.home-page__more {
  font-size: var(--vctn-text-sm);
  font-weight: 500;
  color: var(--vctn-brand);
  text-decoration: none;
}

.home-page__more:hover {
  text-decoration: underline;
}
</style>
