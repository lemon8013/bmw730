<script setup lang="ts">
/**
 * Article detail.
 *
 * The body is rendered from `content_html`, which the backend already produced
 * from the markdown — no client-side markdown parser, and no new dependency.
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import {
  createComment,
  getArticle,
  getAuthor,
  listCategories,
  listComments,
  setArticleFavorite,
  setArticleLike,
} from '@/api/blog'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { useAuthStore } from '@/stores/auth'
import type { Article, Author, Category, Comment } from '@/types/blog'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const articleId = computed(() => String(route.params.id ?? ''))

/**
 * One load for the article plus its author.
 *
 * `getArticle` counts a view on every call, so it must happen exactly once per
 * page visit — hence the two values share a single loader.
 */
const detail = useAsyncData<{ article: Article; author: Author | null }>(async () => {
  const row = await getArticle(articleId.value)
  // A missing author row must not hide an otherwise readable article.
  const who = await getAuthor(row.author_id).catch(() => null)
  return { article: row, author: who }
})

const article = computed(() => detail.data.value?.article ?? null)
const author = computed(() => detail.data.value?.author ?? null)

const categories = useAsyncData(async () => (await listCategories(100)).items)

const category = computed<Category | null>(() => {
  const id = article.value?.category_id
  if (id === null || id === undefined) {
    return null
  }
  return categories.data.value?.find((item) => item.id === id) ?? null
})

const comments = useAsyncData<{ items: Comment[]; total: number }>(async () => {
  const result = await listComments(articleId.value)
  return { items: result.items, total: result.total }
})

const liked = ref(false)
const favorited = ref(false)
const acting = ref(false)

/** Replace the cached article row so counters update without a reload. */
function patchArticle(patch: Partial<Article>): void {
  if (detail.data.value !== null) {
    detail.data.value = { ...detail.data.value, article: { ...article.value!, ...patch } }
  }
}

/** Interaction endpoints need a business identity; offer the way in instead. */
function requireSignIn(): boolean {
  if (auth.isAuthenticated) {
    return true
  }
  ElMessage.info('登录后才能参与互动')
  void router.push({ name: 'login', query: { redirect: route.fullPath } })
  return false
}

async function toggleLike(): Promise<void> {
  if (!requireSignIn() || acting.value) {
    return
  }
  acting.value = true
  try {
    const result = await setArticleLike(articleId.value, !liked.value)
    liked.value = result.liked
    patchArticle({ like_count: result.like_count })
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '操作失败')
  } finally {
    acting.value = false
  }
}

async function toggleFavorite(): Promise<void> {
  if (!requireSignIn() || acting.value) {
    return
  }
  acting.value = true
  try {
    const result = await setArticleFavorite(articleId.value, !favorited.value)
    favorited.value = result.favorited
    patchArticle({ favorite_count: result.favorite_count })
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '操作失败')
  } finally {
    acting.value = false
  }
}

const draft = ref('')
const posting = ref(false)

async function submitComment(): Promise<void> {
  const content = draft.value.trim()
  if (content === '') {
    return
  }
  if (!requireSignIn()) {
    return
  }
  posting.value = true
  try {
    await createComment(articleId.value, { content })
    draft.value = ''
    ElMessage.success('评论已提交，审核通过后可见')
    await comments.reload()
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '评论失败')
  } finally {
    posting.value = false
  }
}

const publishedText = computed(() => {
  const raw = article.value?.published_at
  if (!raw) {
    return ''
  }
  const parsed = new Date(raw)
  return Number.isNaN(parsed.getTime()) ? raw : parsed.toLocaleString('zh-CN')
})
</script>

<template>
  <div class="article-page">
    <FeedState
      :loading="detail.loading.value"
      :failed="detail.failed.value"
      :error="detail.error.value"
      :empty="!detail.loading.value && article === null"
      empty-text="文章不存在或尚未发布"
      @retry="detail.reload()"
    >
      <ElCard v-if="article !== null" shadow="never">
        <h1 class="article-page__title">{{ article.title }}</h1>

        <div class="article-page__meta">
          <span v-if="author !== null">{{ author.author_name }}</span>
          <span v-if="publishedText">{{ publishedText }}</span>
          <RouterLink
            v-if="category"
            :to="{ name: 'category', params: { code: category.category_code } }"
            class="article-page__category"
          >
            {{ category.category_name }}
          </RouterLink>
          <span>{{ article.view_count }} 阅读</span>
        </div>

        <p v-if="article.summary" class="article-page__summary">{{ article.summary }}</p>

        <!--
          `content_html` is produced server side by MarkdownIt and then passed
          through `bleach.clean`, so it never carries raw user HTML.
        -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-if="article.content_html" class="article-body" v-html="article.content_html" />
        <ElEmpty v-else description="这篇文章还没有正文" />

        <div class="article-page__actions">
          <ElButton :type="liked ? 'primary' : 'default'" :loading="acting" @click="toggleLike">
            {{ liked ? '已点赞' : '点赞' }} {{ article.like_count }}
          </ElButton>
          <ElButton
            :type="favorited ? 'primary' : 'default'"
            :loading="acting"
            @click="toggleFavorite"
          >
            {{ favorited ? '已收藏' : '收藏' }} {{ article.favorite_count }}
          </ElButton>
        </div>
      </ElCard>

      <ElCard class="article-page__comments" shadow="never">
        <template #header>
          <span>评论 · {{ comments.data.value?.total ?? 0 }}</span>
        </template>

        <div class="article-page__composer">
          <ElInput
            v-model="draft"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            :placeholder="auth.isAuthenticated ? '写下你的看法…' : '登录后发表评论'"
          />
          <div class="article-page__composer-actions">
            <ElButton v-if="!auth.isAuthenticated" text @click="$router.push({ name: 'login', query: { redirect: $route.fullPath } })">
              去登录
            </ElButton>
            <ElButton type="primary" :loading="posting" @click="submitComment">发表评论</ElButton>
          </div>
        </div>

        <FeedState
          :loading="comments.loading.value"
          :failed="comments.failed.value"
          :error="comments.error.value"
          :empty="!comments.loading.value && (comments.data.value?.items.length ?? 0) === 0"
          empty-text="还没有评论"
          @retry="comments.reload()"
        >
          <div
            v-for="comment in comments.data.value?.items ?? []"
            :key="comment.id"
            class="article-page__comment"
          >
            <div class="article-page__comment-head">
              <ElAvatar :size="24">{{ (comment.user_id ?? '?').slice(0, 1) }}</ElAvatar>
              <span class="article-page__comment-time">
                {{ new Date(comment.created_at).toLocaleString('zh-CN') }}
              </span>
            </div>
            <p class="article-page__comment-body">{{ comment.content }}</p>
          </div>
        </FeedState>
      </ElCard>
    </FeedState>
  </div>
</template>

<style scoped>
.article-page__title {
  margin: 0 0 var(--vctn-space-3);
  color: var(--vctn-text-strong);
  font-size: 26px;
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.article-page__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-3);
  align-items: center;
  margin-bottom: var(--vctn-space-4);
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
}

.article-page__category {
  padding: 2px var(--vctn-space-2);
  border-radius: var(--vctn-radius-sm);
  background-color: var(--vctn-brand-soft);
  color: var(--vctn-brand);
  font-size: var(--vctn-text-xs);
  font-weight: 500;
  text-decoration: none;
}

.article-page__summary {
  margin: 0 0 var(--vctn-space-5);
  padding: var(--vctn-space-3) var(--vctn-space-4);
  border-left: 3px solid var(--vctn-brand);
  border-radius: 0 var(--vctn-radius-md) var(--vctn-radius-md) 0;
  background-color: var(--vctn-brand-softer);
  color: var(--vctn-text-secondary);
  line-height: 1.7;
}

.article-page__actions {
  display: flex;
  gap: var(--vctn-space-2);
  margin-top: var(--vctn-space-6);
  padding-top: var(--vctn-space-4);
  border-top: 1px solid var(--vctn-border-subtle);
}

.article-page__comments {
  margin-top: var(--vctn-space-6);
  padding: var(--vctn-space-4) var(--vctn-space-5);
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
}

.article-page__composer {
  margin-bottom: var(--vctn-space-4);
}

.article-page__composer-actions {
  display: flex;
  gap: var(--vctn-space-2);
  justify-content: flex-end;
  margin-top: var(--vctn-space-2);
}

.article-page__comment {
  padding: var(--vctn-space-3) 0;
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.article-page__comment:last-child {
  border-bottom: none;
}

.article-page__comment-head {
  display: flex;
  gap: var(--vctn-space-2);
  align-items: center;
  margin-bottom: var(--vctn-space-2);
}

.article-page__comment-time {
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.article-page__comment-body {
  margin: 0;
  color: var(--vctn-text-regular);
  line-height: 1.75;
  white-space: pre-wrap;
}
</style>
