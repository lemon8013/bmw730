<script setup lang="ts">
/**
 * Author centre: become an author, then write and submit articles.
 *
 * Everything here needs a business identity, so the page asks for one up front
 * instead of rendering half a screen of 401s.
 */
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import {
  applyAuthor,
  createArticle,
  deleteArticle,
  listArticles,
  listAuthors,
  listCategories,
  publishArticle,
  updateArticle,
} from '@/api/blog'
import FeedState from '@/components/FeedState.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { useAuthStore } from '@/stores/auth'
import type { Article, Author, Category } from '@/types/blog'

const auth = useAuthStore()

const tab = ref<'DRAFT' | 'PUBLISHED'>('DRAFT')

/** My author record, resolved by scanning the directory for my user id. */
const authors = useAsyncData(async () => (await listAuthors(100)).items)
const me = computed<Author | null>(() => {
  const userId = auth.userId
  if (userId === null) {
    return null
  }
  return authors.data.value?.find((item) => item.user_id === userId) ?? null
})

const categories = useAsyncData(async () => (await listCategories(100)).items)

/**
 * My articles, by status.
 *
 * The default feed is published-only; the draft tab asks for `status=DRAFT`,
 * which the backend narrows to the caller's own author row and refuses for
 * anonymous callers.
 */
const feed = useAsyncData<Article[]>(async () => {
  const mine = me.value
  if (mine === null) {
    return []
  }
  const page = await listArticles({ status: tab.value, page: 1, page_size: 100 })
  return page.items
})

watch([tab, () => me.value], () => {
  void feed.reload()
})

// ------------------------------------------------------------ apply form

const applying = ref(false)
const applyForm = reactive({ author_name: '', bio: '', application_reason: '' })
const applyRules: FormRules<typeof applyForm> = {
  author_name: [
    { required: true, message: '请输入作者名', trigger: 'blur' },
    { min: 2, max: 64, message: '作者名长度为 2–64 个字符', trigger: 'blur' },
  ],
}

async function submitApply(): Promise<void> {
  applying.value = true
  try {
    await applyAuthor({
      author_name: applyForm.author_name.trim(),
      bio: applyForm.bio.trim() === '' ? null : applyForm.bio.trim(),
      application_reason:
        applyForm.application_reason.trim() === '' ? null : applyForm.application_reason.trim(),
    })
    ElMessage.success('申请已提交，等待审核')
    await authors.reload()
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '申请失败')
  } finally {
    applying.value = false
  }
}

// ---------------------------------------------------------- article form

const editorOpen = ref(false)
const editingId = ref<string | null>(null)
const saving = ref(false)
const editorFormRef = ref<FormInstance>()

const editorForm = reactive({
  title: '',
  slug: '',
  summary: '' as string | null,
  category_id: null as string | null,
  content_markdown: '',
  tagsText: '',
})

const editorRules: FormRules<typeof editorForm> = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入 slug', trigger: 'blur' },
    {
      pattern: /^[a-z0-9-]+$/,
      message: 'slug 只能包含小写字母、数字和短横线',
      trigger: 'blur',
    },
  ],
}

/** Derive a slug from the title until the user edits it themselves. */
function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
}

watch(
  () => editorForm.title,
  (value) => {
    if (editingId.value === null) {
      editorForm.slug = slugify(value)
    }
  },
)

function openCreate(): void {
  editingId.value = null
  editorForm.title = ''
  editorForm.slug = ''
  editorForm.summary = ''
  editorForm.category_id = null
  editorForm.content_markdown = ''
  editorForm.tagsText = ''
  editorOpen.value = true
}

function openEdit(article: Article): void {
  editingId.value = article.id
  editorForm.title = article.title
  editorForm.slug = article.slug
  editorForm.summary = article.summary
  editorForm.category_id = article.category_id
  editorForm.content_markdown = article.content_markdown ?? ''
  editorForm.tagsText = article.tags.join(', ')
  editorOpen.value = true
}

async function saveArticle(): Promise<void> {
  const form = editorFormRef.value
  if (form === undefined) {
    return
  }
  const valid = await form.validate().catch(() => false)
  if (!valid) {
    return
  }
  const tags = editorForm.tagsText
    .split(/[,，]/)
    .map((tag) => tag.trim())
    .filter((tag) => tag !== '')
  saving.value = true
  try {
    if (editingId.value === null) {
      await createArticle({
        title: editorForm.title.trim(),
        slug: editorForm.slug.trim(),
        summary: editorForm.summary,
        category_id: editorForm.category_id,
        content_markdown: editorForm.content_markdown,
        tags,
      })
      ElMessage.success('草稿已创建')
    } else {
      await updateArticle(editingId.value, {
        title: editorForm.title.trim(),
        slug: editorForm.slug.trim(),
        summary: editorForm.summary,
        category_id: editorForm.category_id,
        content_markdown: editorForm.content_markdown,
        tags,
      })
      ElMessage.success('已保存')
    }
    editorOpen.value = false
    await feed.reload()
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function submitPublish(article: Article): Promise<void> {
  try {
    await publishArticle(article.id)
    ElMessage.success('已提交发布')
    await feed.reload()
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '发布失败')
  }
}

async function removeArticle(article: Article): Promise<void> {
  try {
    await deleteArticle(article.id)
    ElMessage.success('已删除')
    await feed.reload()
  } catch (caught: unknown) {
    ElMessage.error(caught instanceof Error ? caught.message : '删除失败')
  }
}

const statusLabel: Record<string, string> = {
  DRAFT: '草稿',
  PUBLISHED: '已发布',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  NOT_REQUIRED: '无需审核',
}
</script>

<template>
  <div class="mine-page">
    <ElEmpty v-if="!auth.isAuthenticated" description="登录后可使用作者中心">
      <ElButton type="primary" @click="$router.push({ name: 'login', query: { redirect: '/mine' } })">
        去登录
      </ElButton>
    </ElEmpty>

    <template v-else>
      <div class="mine-page__head">
        <h1 class="mine-page__title">作者中心</h1>
        <ElButton v-if="me" type="primary" @click="openCreate">写文章</ElButton>
      </div>

      <ElCard v-if="authors.loading.value" shadow="never">
        <ElSkeleton :rows="2" animated />
      </ElCard>

      <ElCard v-else-if="me === null" shadow="never" class="mine-page__apply">
        <template #header><span>申请成为作者</span></template>
        <ElForm :model="applyForm" :rules="applyRules" label-position="top">
          <ElFormItem label="作者名" prop="author_name">
            <ElInput v-model="applyForm.author_name" placeholder="展示在文章上的名字" />
          </ElFormItem>
          <ElFormItem label="简介">
            <ElInput v-model="applyForm.bio" type="textarea" :rows="2" />
          </ElFormItem>
          <ElFormItem label="申请理由">
            <ElInput v-model="applyForm.application_reason" type="textarea" :rows="2" />
          </ElFormItem>
          <ElButton type="primary" :loading="applying" @click="submitApply">提交申请</ElButton>
        </ElForm>
      </ElCard>

      <template v-else>
        <ElDescriptions :column="2" border class="mine-page__profile">
          <ElDescriptionsItem label="作者名">{{ me.author_name }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">{{ statusLabel[me.status] ?? me.status }}</ElDescriptionsItem>
        </ElDescriptions>

        <ElTabs v-model="tab" class="mine-page__tabs">
          <ElTabPane label="草稿" name="DRAFT" />
          <ElTabPane label="已发布" name="PUBLISHED" />
        </ElTabs>

        <FeedState
          :loading="feed.loading.value"
          :failed="feed.failed.value"
          :error="feed.error.value"
          :empty="!feed.loading.value && (feed.data.value?.length ?? 0) === 0"
          empty-text="还没有文章"
          @retry="feed.reload()"
        >
          <ElTable :data="feed.data.value ?? []" border>
            <ElTableColumn prop="title" label="标题" min-width="220" />
            <ElTableColumn prop="review_status" label="审核" width="110">
              <template #default="{ row }">
                {{ statusLabel[row.review_status] ?? row.review_status }}
              </template>
            </ElTableColumn>
            <ElTableColumn prop="view_count" label="阅读" width="90" />
            <ElTableColumn label="操作" width="220">
              <template #default="{ row }">
                <ElButton size="small" text @click="openEdit(row)">编辑</ElButton>
                <ElButton
                  v-if="row.status !== 'PUBLISHED'"
                  size="small"
                  text
                  type="primary"
                  @click="submitPublish(row)"
                >
                  发布
                </ElButton>
                <ElButton size="small" text type="danger" @click="removeArticle(row)">
                  删除
                </ElButton>
              </template>
            </ElTableColumn>
          </ElTable>
        </FeedState>
      </template>
    </template>

    <ElDialog
      v-model="editorOpen"
      :title="editingId === null ? '写文章' : '编辑文章'"
      width="720px"
    >
      <ElForm ref="editorFormRef" :model="editorForm" :rules="editorRules" label-position="top">
        <ElFormItem label="标题" prop="title">
          <ElInput v-model="editorForm.title" />
        </ElFormItem>
        <ElFormItem label="slug" prop="slug">
          <ElInput v-model="editorForm.slug" placeholder="url 中的短名，如 hello-world" />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElSelect v-model="editorForm.category_id" clearable placeholder="不选则无分类">
            <ElOption
              v-for="category in (categories.data.value ?? []) as Category[]"
              :key="category.id"
              :label="category.category_name"
              :value="category.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="摘要">
          <ElInput v-model="editorForm.summary" type="textarea" :rows="2" />
        </ElFormItem>
        <ElFormItem label="标签">
          <ElInput v-model="editorForm.tagsText" placeholder="用逗号分隔，如：实践,工具" />
        </ElFormItem>
        <ElFormItem label="正文（Markdown）">
          <ElInput v-model="editorForm.content_markdown" type="textarea" :rows="12" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editorOpen = false">取消</ElButton>
        <ElButton type="primary" :loading="saving" @click="saveArticle">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.mine-page__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--vctn-space-3);
  padding-bottom: var(--vctn-space-3);
  margin-bottom: var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.mine-page__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.mine-page__apply {
  margin-bottom: 16px;
}

.mine-page__profile {
  margin-bottom: 16px;
}
</style>
