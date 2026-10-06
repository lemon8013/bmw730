<script setup lang="ts">
/** 文章管理：文章查询、创建、编辑、删除与发布；正文以纯文本展示（不渲染 Markdown）。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElDescriptions,
  ElDescriptionsItem,
  ElDrawer,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
  ElTag,
  type FormRules,
} from 'element-plus'

import {
  createArticle,
  deleteArticle,
  getArticle,
  listArticles,
  listCategories,
  publishArticle,
  updateArticle,
} from '@/api/blog'
import PageHeader from '@/components/common/PageHeader.vue'
import DataStateView from '@/components/common/DataStateView.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseDialog from '@/components/dialog/BaseDialog.vue'
import BaseForm from '@/components/form/BaseForm.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { usePagination } from '@/composables/usePagination'
import { PERMISSION } from '@/constants/permissions'
import { usePermissionStore } from '@/stores/permission'
import type { Article, ArticleCreateRequest, ArticleUpdateRequest } from '@/types/blog'
import { ARTICLE_STATUS, STATUS_LABEL } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime, formatNumber } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.blogArticlePublish)

/** 是否具备发布权限。 */
const canPublish = computed(() => permission.has(PERMISSION.blogArticlePublish))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function statusLabel(value: string): string {
  return STATUS_LABEL[value] ?? value
}

/** 审核状态的中文标签；PENDING 在审核语境下译为“待审核”。 */
const REVIEW_STATUS_LABEL: Readonly<Record<string, string>> = {
  NOT_REQUIRED: '无需审核',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
}

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const keyword = ref('')
const categoryId = ref('')
const status = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listArticles({
    keyword: keyword.value.trim() === '' ? undefined : keyword.value.trim(),
    category_id: categoryId.value === '' ? undefined : categoryId.value,
    status: status.value === '' ? undefined : status.value,
    page: page.value,
    page_size: pageSize.value,
  }),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

/** 分类下拉数据源。 */
const {
  data: categories,
  loading: categoriesLoading,
  failed: categoriesFailed,
  error: categoriesError,
  reload: reloadCategories,
} = useAsyncData(() => listCategories({ page: 1, page_size: 100 }))

const categoryOptions = computed(() => categories.value?.items ?? [])

function categoryName(id: string | null | undefined): string {
  if (id === null || id === undefined) {
    return '—'
  }
  const found = categoryOptions.value.find((item) => item.id === id)
  return found?.category_name ?? id
}

function onSearch(): void {
  changePage(1)
  void reload()
}

function onReset(): void {
  keyword.value = ''
  categoryId.value = ''
  status.value = ''
  changePage(1)
  void reload()
}

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

// ---------------------------------------------------------------------------
// 表单
// ---------------------------------------------------------------------------

interface ArticleFormModel {
  title: string
  slug: string
  summary: string
  cover_url: string
  category_id: string
  content_markdown: string
  tags: string[]
}

const formModel = reactive<ArticleFormModel>({
  title: '',
  slug: '',
  summary: '',
  cover_url: '',
  category_id: '',
  content_markdown: '',
  tags: [],
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  slug: [{ required: true, message: '请输入 Slug', trigger: 'blur' }],
}

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()
const newTag = ref('')

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function addTag(): void {
  const value = newTag.value.trim()
  if (value === '' || formModel.tags.includes(value)) {
    newTag.value = ''
    return
  }
  formModel.tags.push(value)
  newTag.value = ''
}

function removeTag(tag: string): void {
  formModel.tags = formModel.tags.filter((item) => item !== tag)
}

function openCreate(): void {
  editingId.value = null
  formModel.title = ''
  formModel.slug = ''
  formModel.summary = ''
  formModel.cover_url = ''
  formModel.category_id = ''
  formModel.content_markdown = ''
  formModel.tags = []
  newTag.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const article = row as unknown as Article
  editingId.value = article.id
  formModel.title = article.title
  formModel.slug = article.slug
  formModel.summary = article.summary ?? ''
  formModel.cover_url = article.cover_url ?? ''
  formModel.category_id = article.category_id ?? ''
  formModel.content_markdown = article.content_markdown ?? ''
  formModel.tags = [...(article.tags ?? [])]
  newTag.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

function reportSubmitError(caught: unknown): void {
  const rendered = renderError(caught)
  submitError.value = rendered.message
  submitTrace.value = rendered.traceId ?? null
}

async function submit(): Promise<void> {
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    const summary = formModel.summary.trim()
    const coverUrl = formModel.cover_url.trim()
    const categoryIdValue = formModel.category_id === '' ? null : formModel.category_id
    if (editingId.value === null) {
      const payload: ArticleCreateRequest = {
        title: formModel.title,
        slug: formModel.slug,
        summary: summary === '' ? null : summary,
        cover_url: coverUrl === '' ? null : coverUrl,
        category_id: categoryIdValue,
        content_markdown: formModel.content_markdown,
        tags: [...formModel.tags],
      }
      await createArticle(payload)
      notify.success('文章已创建')
    } else {
      const payload: ArticleUpdateRequest = {
        title: formModel.title,
        slug: formModel.slug,
        summary: summary === '' ? null : summary,
        cover_url: coverUrl === '' ? null : coverUrl,
        category_id: categoryIdValue,
        content_markdown: formModel.content_markdown,
        tags: [...formModel.tags],
      }
      await updateArticle(editingId.value, payload)
      notify.success('文章已更新')
    }
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

async function onPublish(row: Record<string, unknown>): Promise<void> {
  const article = row as unknown as Article
  const confirmed = await notify.confirm({
    title: '发布文章',
    message: `确定要发布文章「${article.title}」吗？`,
  })
  if (!confirmed) {
    return
  }
  try {
    await publishArticle(article.id)
    notify.success('文章已发布')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const article = row as unknown as Article
  const confirmed = await notify.confirm({
    title: '删除文章',
    message: `确定要删除文章「${article.title}」吗？该操作不可撤销。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteArticle(article.id)
    notify.success('文章已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}

// ---------------------------------------------------------------------------
// 详情抽屉
// ---------------------------------------------------------------------------

const detailVisible = ref(false)
const detailId = ref<string | null>(null)

const {
  data: detail,
  loading: detailLoading,
  failed: detailFailed,
  error: detailError,
  reload: reloadDetail,
} = useAsyncData<Article | null>(
  () => {
    const id = detailId.value
    if (id === null) {
      return Promise.resolve(null)
    }
    return getArticle(id)
  },
  { immediate: false, initial: null },
)

function openDetail(row: Record<string, unknown>): void {
  const article = row as unknown as Article
  detailId.value = article.id
  detailVisible.value = true
  void reloadDetail()
}
</script>

<template>
  <div class="article-list-page">
    <PageHeader title="文章管理" description="维护博客文章、标签与正文；发布需要 BLOG_ARTICLE_PUBLISH 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton type="primary" @click="openCreate">新建文章</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="article-list-page__filters">
      <p v-if="categoriesFailed" class="article-list-page__trace">
        分类加载失败：{{ categoriesError?.message ?? '请稍后重试' }}
        <template v-if="categoriesError?.traceId">
          （Trace ID: {{ categoriesError.traceId }}）
        </template>
        <ElButton link type="primary" @click="reloadCategories">重试</ElButton>
      </p>
      <ElSpace wrap>
        <ElInput
          v-model="keyword"
          placeholder="按标题 / Slug 搜索"
          clearable
          style="width: 220px"
          @keyup.enter="onSearch"
        />
        <ElSelect
          v-model="categoryId"
          placeholder="分类"
          clearable
          :loading="categoriesLoading"
          style="width: 200px"
        >
          <ElOption
            v-for="item in categoryOptions"
            :key="item.id"
            :label="item.category_name"
            :value="item.id"
          />
        </ElSelect>
        <ElSelect v-model="status" placeholder="状态" clearable style="width: 140px">
          <ElOption
            v-for="item in ARTICLE_STATUS"
            :key="item"
            :label="statusLabel(item)"
            :value="item"
          />
        </ElSelect>
        <ElButton type="primary" @click="onSearch">查询</ElButton>
        <ElButton @click="onReset">重置</ElButton>
      </ElSpace>
    </ElCard>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无文章"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('title')"
          prop="title"
          label="标题"
          min-width="220"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('slug')"
          prop="slug"
          label="Slug"
          min-width="160"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('category_id')"
          label="分类"
          width="140"
        >
          <template #default="{ row }">{{ categoryName(row.category_id) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('review_status')"
          prop="review_status"
          label="审核状态"
          width="110"
        >
          <template #default="{ row }">
            <StatusTag :value="row.review_status" :labels="REVIEW_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('view_count')" label="浏览" width="90">
          <template #default="{ row }">{{ formatNumber(row.view_count) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('comment_count')" label="评论" width="90">
          <template #default="{ row }">{{ formatNumber(row.comment_count) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('published_at')"
          label="发布时间"
          width="180"
        >
          <template #default="{ row }">{{ formatDateTime(row.published_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
              <ElButton link type="primary" @click="openEdit(row)">编辑</ElButton>
              <ElButton
                v-if="canPublish"
                v-permission="PERMISSION.blogArticlePublish"
                link
                type="success"
                @click="onPublish(row)"
              >
                发布
              </ElButton>
              <ElButton link type="danger" @click="onDelete(row)">删除</ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新建文章' : '编辑文章'"
      :confirm-loading="submitting"
      width="720px"
      @confirm="submit"
    >
      <BaseForm
        ref="formRef"
        :model="formModel"
        :rules="rules"
        :error-message="submitError"
        :error-trace-id="submitTrace"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('title')" label="标题" prop="title">
          <ElInput v-model="formModel.title" :disabled="fields.isReadOnly('title')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('slug')" label="Slug" prop="slug">
          <ElInput v-model="formModel.slug" :disabled="fields.isReadOnly('slug')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('category_id')" label="分类">
          <ElSelect
            v-model="formModel.category_id"
            clearable
            placeholder="选择分类"
            :disabled="fields.isReadOnly('category_id')"
          >
            <ElOption
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.category_name"
              :value="item.id"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('summary')" label="摘要">
          <ElInput
            v-model="formModel.summary"
            type="textarea"
            :rows="2"
            :disabled="fields.isReadOnly('summary')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('cover_url')" label="封面地址">
          <ElInput
            v-model="formModel.cover_url"
            :disabled="fields.isReadOnly('cover_url')"
            placeholder="https://…"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('tags')" label="标签">
          <div class="article-list-page__tags">
            <ElTag
              v-for="tag in formModel.tags"
              :key="tag"
              closable
              size="small"
              @close="removeTag(tag)"
            >
              {{ tag }}
            </ElTag>
          </div>
          <ElSpace class="article-list-page__tag-input">
            <ElInput
              v-model="newTag"
              placeholder="输入标签后回车添加"
              style="width: 220px"
              :disabled="fields.isReadOnly('tags')"
              @keyup.enter="addTag"
            />
            <ElButton :disabled="fields.isReadOnly('tags')" @click="addTag">添加</ElButton>
          </ElSpace>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('content_markdown')" label="正文（Markdown）">
          <ElInput
            v-model="formModel.content_markdown"
            type="textarea"
            :rows="10"
            :disabled="fields.isReadOnly('content_markdown')"
            placeholder="以 Markdown 纯文本保存"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <ElDrawer v-model="detailVisible" title="文章详情" size="720px" destroy-on-close>
      <DataStateView
        :loading="detailLoading"
        :failed="detailFailed"
        :error="detailError"
        :empty="detail === null"
        empty-text="未找到该文章"
        @retry="reloadDetail"
      >
        <template v-if="detail">
          <ElDescriptions :column="2" border>
            <ElDescriptionsItem label="标题" :span="2">{{ detail.title }}</ElDescriptionsItem>
            <ElDescriptionsItem label="Slug">{{ detail.slug }}</ElDescriptionsItem>
            <ElDescriptionsItem label="分类">
              {{ categoryName(detail.category_id) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="状态">
              <StatusTag :value="detail.status" />
            </ElDescriptionsItem>
            <ElDescriptionsItem label="审核状态">
              <StatusTag :value="detail.review_status" :labels="REVIEW_STATUS_LABEL" />
            </ElDescriptionsItem>
            <ElDescriptionsItem label="浏览">{{ formatNumber(detail.view_count) }}</ElDescriptionsItem>
            <ElDescriptionsItem label="点赞">{{ formatNumber(detail.like_count) }}</ElDescriptionsItem>
            <ElDescriptionsItem label="收藏">
              {{ formatNumber(detail.favorite_count) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="评论">
              {{ formatNumber(detail.comment_count) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="发布时间">
              {{ formatDateTime(detail.published_at) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="更新时间">
              {{ formatDateTime(detail.updated_at) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="标签" :span="2">
              <template v-if="detail.tags && detail.tags.length">
                <ElTag
                  v-for="tag in detail.tags"
                  :key="tag"
                  size="small"
                  class="article-list-page__detail-tag"
                >
                  {{ tag }}
                </ElTag>
              </template>
              <span v-else>—</span>
            </ElDescriptionsItem>
          </ElDescriptions>
          <h4 class="article-list-page__section-title">正文（纯文本）</h4>
          <pre class="article-list-page__content">{{ detail.content_markdown ?? '—' }}</pre>
        </template>
      </DataStateView>
    </ElDrawer>
  </div>
</template>

<style scoped>
.article-list-page__filters {
  margin-bottom: 16px;
}

.article-list-page__trace {
  margin: 0 0 12px;
  color: var(--vctn-text-secondary);
  font-size: 12px;
  word-break: break-all;
}

.article-list-page__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.article-list-page__tag-input {
  width: 100%;
}

.article-list-page__detail-tag {
  margin: 0 8px 8px 0;
}

.article-list-page__section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 500;
}

.article-list-page__content {
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--vctn-border-subtle);
  border-radius: 4px;
  background-color: var(--vctn-bg-hover);
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
