<script setup lang="ts">
/** One author plus their published articles. */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { getAuthor, listArticles } from '@/api/blog'
import ArticleCard from '@/components/ArticleCard.vue'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { useAuthStore } from '@/stores/auth'
import type { Article, Author } from '@/types/blog'

const route = useRoute()
const auth = useAuthStore()

const authorId = computed(() => String(route.params.id ?? ''))

const author = useAsyncData<Author>(() => getAuthor(authorId.value))

/** Published articles by this author, filtered server side. */
const articles = useAsyncData<Article[]>(async () => {
  const page = await listArticles({ author_id: authorId.value, page: 1, page_size: 100 })
  return page.items
})

/** The signed-in user can follow this author's account. */
const isSelf = computed(() => auth.userId !== null && auth.userId === author.data.value?.user_id)
</script>

<template>
  <div class="author-page">
    <FeedState
      :loading="author.loading.value"
      :failed="author.failed.value"
      :error="author.error.value"
      :empty="!author.loading.value && author.data.value === null"
      empty-text="作者不存在"
      @retry="author.reload()"
    >
      <ElCard v-if="author.data.value" shadow="never" class="author-page__profile">
        <div class="author-page__head">
          <ElAvatar :size="56">{{ author.data.value.author_name.slice(0, 1) }}</ElAvatar>
          <div>
            <h1 class="author-page__name">{{ author.data.value.author_name }}</h1>
            <p v-if="author.data.value.bio" class="author-page__bio">
              {{ author.data.value.bio }}
            </p>
          </div>
          <ElTag v-if="isSelf" type="info" size="small" class="author-page__self">我自己</ElTag>
        </div>
      </ElCard>

      <h2 class="author-page__section">已发布文章</h2>

      <FeedState
        :loading="articles.loading.value"
        :failed="articles.failed.value"
        :error="articles.error.value"
        :empty="!articles.loading.value && (articles.data.value?.length ?? 0) === 0"
        empty-text="这位作者还没有已发布的文章"
        @retry="articles.reload()"
      >
        <ArticleCard v-for="item in articles.data.value ?? []" :key="item.id" :article="item" />
      </FeedState>
    </FeedState>
  </div>
</template>

<style scoped>
.author-page__profile {
  margin-bottom: 16px;
}

.author-page__head {
  display: flex;
  gap: 14px;
  align-items: center;
}

.author-page__name {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.author-page__bio {
  margin: 4px 0 0;
  color: var(--vctn-text-secondary);
  font-size: 13px;
}

.author-page__self {
  margin-left: auto;
}

.author-page__section {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-2);
  margin: 0 0 var(--vctn-space-3);
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-base);
  font-weight: 500;
}

.author-page__section::before {
  content: '';
  width: 3px;
  height: 14px;
  border-radius: var(--vctn-radius-pill);
  background-color: var(--vctn-brand);
}
</style>
