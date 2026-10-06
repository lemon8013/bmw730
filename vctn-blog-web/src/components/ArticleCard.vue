<script setup lang="ts">
/** One article in a feed: cover, title, summary, tags and counters. */
import { computed } from 'vue'

import type { Article } from '@/types/blog'

const props = defineProps<{ article: Article }>()

/** The backend returns ISO 8601 in UTC; show it as a plain date. */
const publishedText = computed(() => {
  const raw = props.article.published_at ?? props.article.created_at
  if (raw === null) {
    return '未发布'
  }
  const parsed = new Date(raw)
  return Number.isNaN(parsed.getTime())
    ? raw
    : parsed.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
})
</script>

<template>
  <ElCard class="article-card" shadow="hover">
    <div class="article-card__body">
      <div v-if="article.cover_url" class="article-card__cover">
        <img :src="article.cover_url" :alt="article.title" />
      </div>

      <div class="article-card__content">
        <RouterLink
          :to="{ name: 'article', params: { id: article.id } }"
          class="article-card__title"
        >
          {{ article.title }}
        </RouterLink>

        <p v-if="article.summary" class="article-card__summary">{{ article.summary }}</p>

        <div class="article-card__meta">
          <span>{{ publishedText }}</span>
          <span class="article-card__dot">·</span>
          <span>{{ article.view_count }} 阅读</span>
          <span class="article-card__dot">·</span>
          <span>{{ article.like_count }} 点赞</span>
          <span class="article-card__dot">·</span>
          <span>{{ article.comment_count }} 评论</span>
        </div>

        <!--
          The backend has no tag filter, so a tag leads to the keyword search
          rather than pretending to be a real tag archive.
        -->
        <div v-if="article.tags.length > 0" class="article-card__tags">
          <RouterLink
            v-for="tag in article.tags"
            :key="tag"
            :to="{ name: 'search', query: { keyword: tag } }"
            class="article-card__tag"
          >
            #{{ tag }}
          </RouterLink>
        </div>
      </div>
    </div>
  </ElCard>
</template>

<style scoped>
.article-card {
  margin-bottom: var(--vctn-space-3);
  border-radius: var(--vctn-radius-lg);
  transition:
    border-color var(--vctn-duration-base) var(--vctn-ease),
    box-shadow var(--vctn-duration-base) var(--vctn-ease);
}

.article-card:hover {
  border-color: var(--vctn-border-brand);
}

.article-card :deep(.el-card__body) {
  padding: var(--vctn-space-4) var(--vctn-space-5);
}

.article-card__body {
  display: flex;
  gap: var(--vctn-space-4);
}

.article-card__cover {
  flex: none;
  width: 148px;
  height: 96px;
  overflow: hidden;
  border-radius: var(--vctn-radius-md);
  background-color: var(--vctn-bg-subtle);
}

.article-card__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.article-card__content {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--vctn-space-2);
  min-width: 0;
}

.article-card__title {
  color: var(--vctn-text-strong);
  font-size: 17px;
  font-weight: 500;
  line-height: 1.45;
  letter-spacing: -0.01em;
  text-decoration: none;
  transition: color var(--vctn-duration-fast) var(--vctn-ease);
}

.article-card__title:hover {
  color: var(--vctn-brand);
}

.article-card__summary {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
  line-height: 1.7;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.article-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-2);
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.article-card__dot {
  opacity: 0.5;
}

.article-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-2);
}

.article-card__tag {
  padding: 2px var(--vctn-space-2);
  border-radius: var(--vctn-radius-sm);
  background-color: var(--vctn-brand-softer);
  color: var(--vctn-brand);
  font-size: var(--vctn-text-xs);
  text-decoration: none;
  transition: background-color var(--vctn-duration-fast) var(--vctn-ease);
}

.article-card__tag:hover {
  background-color: var(--vctn-brand-soft);
}

@media (max-width: 640px) {
  .article-card__body {
    flex-direction: column;
  }

  .article-card__cover {
    width: 100%;
    height: 160px;
  }
}
</style>
