<script setup lang="ts">
/**
 * Articles of one category.
 *
 * The backend filters articles by `category_id`, while the URL carries the
 * stable `category_code`, so the code is resolved to an id first.
 */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { listArticles, listCategories } from '@/api/blog'
import ArticleCard from '@/components/ArticleCard.vue'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import type { Article, Category } from '@/types/blog'

const route = useRoute()
const page = ref(1)

const code = computed(() => String(route.params.code ?? ''))

const categories = useAsyncData(async () => (await listCategories(100)).items)

const category = computed<Category | null>(
  () => categories.data.value?.find((item) => item.category_code === code.value) ?? null,
)

const feed = useAsyncData<{ items: Article[]; total: number }>(async () => {
  const target = category.value
  if (target === null) {
    return { items: [], total: 0 }
  }
  const result = await listArticles({
    category_id: target.id,
    page: page.value,
    page_size: 10,
  })
  return { items: result.items, total: result.total }
})

watch([() => categories.data.value, page], () => {
  void feed.reload()
})

const items = computed(() => feed.data.value?.items ?? [])
const total = computed(() => feed.data.value?.total ?? 0)
const unresolved = computed(() => !categories.loading.value && category.value === null)
</script>

<template>
  <div class="category-page">
    <div class="category-page__head">
      <h1 class="category-page__title">{{ category?.category_name ?? '分类' }}</h1>
      <span v-if="category" class="category-page__count">共 {{ total }} 篇</span>
    </div>

    <p v-if="category?.description" class="category-page__desc">{{ category.description }}</p>

    <ElEmpty v-if="unresolved" description="分类不存在或已下线" />

    <FeedState
      v-else
      :loading="feed.loading.value"
      :failed="feed.failed.value"
      :error="feed.error.value"
      :empty="!feed.loading.value && items.length === 0"
      empty-text="该分类下还没有已发布的文章"
      @retry="feed.reload()"
    >
      <ArticleCard v-for="article in items" :key="article.id" :article="article" />

      <ElPagination
        v-if="total > 10"
        v-model:current-page="page"
        class="category-page__pager"
        layout="prev, pager, next"
        :total="total"
        :page-size="10"
      />
    </FeedState>
  </div>
</template>

<style scoped>
.category-page__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--vctn-space-3);
  padding-bottom: var(--vctn-space-3);
  margin-bottom: var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.category-page__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.category-page__count {
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.category-page__desc {
  margin: 0 0 12px;
  color: var(--vctn-text-secondary);
  font-size: 13px;
}

.category-page__pager {
  margin-top: var(--vctn-space-4);
  padding: var(--vctn-space-3);
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  justify-content: center;
}
</style>
