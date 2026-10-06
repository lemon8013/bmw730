<script setup lang="ts">
/** Published article feed. */
import { computed, ref, watch } from 'vue'

import { listArticles } from '@/api/blog'
import ArticleCard from '@/components/ArticleCard.vue'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { Article, ArticleQuery } from '@/types/blog'

const page = ref(1)
const pageSize = ref(10)

const feed = useAsyncData<{ items: Article[]; total: number }>(async () => {
  const query: ArticleQuery = { page: page.value, page_size: pageSize.value }
  const result = await listArticles(query)
  return { items: result.items, total: result.total }
})

// Paging is driven from the table below, so reloading has to be explicit.
watch([page, pageSize], () => {
  void feed.reload()
})

const total = computed(() => feed.data.value?.total ?? 0)
const items = computed(() => feed.data.value?.items ?? [])
</script>

<template>
  <div class="home-page">
    <div class="home-page__head">
      <h1 class="home-page__title">最新文章</h1>
      <span class="home-page__count">共 {{ total }} 篇</span>
    </div>

    <FeedState
      :loading="feed.loading.value"
      :failed="feed.failed.value"
      :error="feed.error.value"
      :empty="!feed.loading.value && items.length === 0"
      empty-text="还没有已发布的文章"
      @retry="feed.reload()"
    >
      <ArticleCard v-for="article in items" :key="article.id" :article="article" />

      <ElPagination
        v-if="total > pageSize"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="home-page__pager"
        layout="total, sizes, prev, pager, next"
        :total="total"
        :page-sizes="[10, 20, 50]"
      />
    </FeedState>
  </div>
</template>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
}

.home-page__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--vctn-space-3);
  padding-bottom: var(--vctn-space-3);
  margin-bottom: var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.home-page__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.home-page__count {
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.home-page__pager {
  margin-top: var(--vctn-space-4);
  padding: var(--vctn-space-3);
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  justify-content: center;
}
</style>
