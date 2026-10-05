<script setup lang="ts">
/** Search results for `?keyword=…`. */
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElCard } from 'element-plus'

import { searchTools } from '@/api/tools'
import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AsyncSection from '@/components/AsyncSection.vue'
import ToolCard from '@/components/ToolCard.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { ToolCatalogItem } from '@/types/catalog'

const route = useRoute()
const keyword = computed(() => String(route.query.keyword ?? '').trim())

const state = useAsyncData<ToolCatalogItem[]>(() =>
  keyword.value === '' ? Promise.resolve([]) : searchTools(keyword.value),
)

// Re-run whenever the query string changes (in-app navigation between searches).
watch(keyword, () => {
  void state.reload()
})
</script>

<template>
  <div class="search-page">
    <AppBreadcrumb :entries="[{ label: `搜索：${keyword === '' ? '（未输入关键词）' : keyword}` }]" />

    <ElCard shadow="never" class="search-page__head">
      <h1 class="search-page__title">搜索：{{ keyword === '' ? '（请输入关键词）' : keyword }}</h1>
    </ElCard>

    <ElCard shadow="never">
      <AsyncSection
        :loading="state.loading.value"
        :failed="state.failed.value"
        :error="state.error.value"
        :empty="(state.data.value ?? []).length === 0"
        empty-text="没有匹配的工具，换个关键词试试"
        @retry="state.reload"
      >
        <div class="search-page__grid">
          <ToolCard v-for="tool in state.data.value ?? []" :key="tool.id" :tool="tool" />
        </div>
      </AsyncSection>
    </ElCard>
  </div>
</template>

<style scoped>
.search-page__head {
  margin-bottom: 16px;
}

.search-page__title {
  margin: 0;
  font-size: 18px;
}

.search-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
</style>
