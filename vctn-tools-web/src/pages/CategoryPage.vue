<script setup lang="ts">
/** One category: its tools as cards. The slug is the category code. */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElCard } from 'element-plus'

import { listToolCategories, listTools } from '@/api/tools'
import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AsyncSection from '@/components/AsyncSection.vue'
import ToolCard from '@/components/ToolCard.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { ToolCatalogItem, ToolCategoryItem } from '@/types/catalog'

const route = useRoute()
const slug = computed(() => String(route.params.slug ?? ''))

const categoriesState = useAsyncData<ToolCategoryItem[]>(() => listToolCategories())
const toolsState = useAsyncData<ToolCatalogItem[]>(() => listTools())

const category = computed<ToolCategoryItem | undefined>(() =>
  (categoriesState.data.value ?? []).find((item) => item.category_code === slug.value),
)

const tools = computed<ToolCatalogItem[]>(() => {
  const target = category.value
  if (target === undefined) {
    return []
  }
  return (toolsState.data.value ?? []).filter((tool) => tool.category_id === target.id)
})
</script>

<template>
  <div class="category-page">
    <AppBreadcrumb :entries="[{ label: category?.category_name ?? '分类' }]" />

    <ElCard shadow="never" class="category-page__head">
      <template v-if="category !== undefined">
        <h1 class="category-page__title">{{ category.category_name }}</h1>
        <p class="category-page__desc">{{ category.description ?? '该分类下的全部工具。' }}</p>
      </template>
      <template v-else>
        <h1 class="category-page__title">分类</h1>
        <p class="category-page__desc">正在加载分类信息…</p>
      </template>
    </ElCard>

    <ElCard shadow="never">
      <AsyncSection
        :loading="toolsState.loading.value || categoriesState.loading.value"
        :failed="toolsState.failed.value || categoriesState.failed.value"
        :error="toolsState.error.value ?? categoriesState.error.value"
        :empty="tools.length === 0"
        empty-text="该分类下暂无工具"
        @retry="() => { void toolsState.reload(); void categoriesState.reload() }"
      >
        <div class="category-page__grid">
          <ToolCard v-for="tool in tools" :key="tool.id" :tool="tool" />
        </div>
      </AsyncSection>
    </ElCard>
  </div>
</template>

<style scoped>
.category-page__head {
  margin-bottom: 16px;
}

.category-page__title {
  margin: 0 0 6px;
  font-size: 20px;
}

.category-page__desc {
  margin: 0;
  color: var(--el-text-color-secondary);
}

.category-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
</style>
