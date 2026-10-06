<script setup lang="ts">
/** Keyword search over published articles. */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { listArticles } from '@/api/blog'
import ArticleCard from '@/components/ArticleCard.vue'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { Article } from '@/types/blog'

const route = useRoute()
const page = ref(1)

const keyword = computed(() => {
  const raw = route.query.keyword
  return typeof raw === 'string' ? raw.trim() : ''
})

const feed = useAsyncData<{ items: Article[]; total: number }>(async () => {
  const result = await listArticles({ keyword: keyword.value, page: page.value, page_size: 10 })
  return { items: result.items, total: result.total }
})

watch([keyword, page], () => {
  void feed.reload()
})

const items = computed(() => feed.data.value?.items ?? [])
const total = computed(() => feed.data.value?.total ?? 0)
</script>

<template>
  <div class="search-page">
    <div class="search-page__head">
      <h1 class="search-page__title">
        {{ keyword === '' ? '搜索' : `“${keyword}” 的搜索结果` }}
      </h1>
      <span v-if="keyword !== ''" class="search-page__count">共 {{ total }} 篇</span>
    </div>

    <FeedState
      :loading="feed.loading.value"
      :failed="feed.failed.value"
      :error="feed.error.value"
      :empty="!feed.loading.value && items.length === 0"
      :empty-text="keyword === '' ? '请输入关键词' : '没有匹配的文章'"
      @retry="feed.reload()"
    >
      <ArticleCard v-for="article in items" :key="article.id" :article="article" />

      <ElPagination
        v-if="total > 10"
        v-model:current-page="page"
        class="search-page__pager"
        layout="prev, pager, next"
        :total="total"
        :page-size="10"
      />
    </FeedState>
  </div>
</template>

<style scoped>
.search-page__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--vctn-space-3);
  padding-bottom: var(--vctn-space-3);
  margin-bottom: var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.search-page__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.search-page__count {
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.search-page__pager {
  margin-top: var(--vctn-space-4);
  padding: var(--vctn-space-3);
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  justify-content: center;
}
</style>
