<script setup lang="ts">
/** 文章审核：审核队列、通过 / 驳回，正文以纯文本展示。 */
import { computed, ref, watch } from 'vue'
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
  type FormRules,
} from 'element-plus'

import { getArticle, listReviewQueue, reviewArticle } from '@/api/blog'
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
import type { Article, ArticleReviewRequest } from '@/types/blog'
import { REVIEW_DECISION, STATUS_LABEL, type ReviewDecision } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime, formatNumber } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.blogArticleReview)

/** 是否具备文章审核权限。 */
const canReview = computed(() => permission.has(PERMISSION.blogArticleReview))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function decisionLabel(decision: string): string {
  return STATUS_LABEL[decision] ?? decision
}

/** 审核状态的中文标签；PENDING 在审核语境下译为“待审核”。 */
const REVIEW_STATUS_LABEL: Readonly<Record<string, string>> = {
  NOT_REQUIRED: '无需审核',
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
}

// ---------------------------------------------------------------------------
// 审核队列
// ---------------------------------------------------------------------------

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listReviewQueue(page.value, pageSize.value),
)

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

// ---------------------------------------------------------------------------
// 审核对话框
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const reviewing = ref<Article | null>(null)
const decision = ref<ReviewDecision>('APPROVED')
const reviewComment = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

const rules: FormRules = {
  decision: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
}

const formModel = computed(() => ({
  decision: decision.value,
  review_comment: reviewComment.value,
}))

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openReview(row: Record<string, unknown>, preset: ReviewDecision): void {
  reviewing.value = row as unknown as Article
  decision.value = preset
  reviewComment.value = ''
  clearSubmitError()
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  const article = reviewing.value
  if (article === null) {
    return
  }
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  clearSubmitError()
  submitting.value = true
  try {
    const comment = reviewComment.value.trim()
    const payload: ArticleReviewRequest = {
      decision: decision.value,
      review_comment: comment === '' ? null : comment,
    }
    await reviewArticle(article.id, payload)
    notify.success(decision.value === 'APPROVED' ? '文章已通过审核' : '文章已驳回')
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    const rendered = renderError(caught)
    submitError.value = rendered.message
    submitTrace.value = rendered.traceId ?? null
  } finally {
    submitting.value = false
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
  <div class="article-review-page">
    <PageHeader title="文章审核" description="处理待审核文章；审核操作需要 BLOG_ARTICLE_REVIEW 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="total"
        :page="page"
        :page-size="pageSize"
        empty-text="暂无待审核文章"
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
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="提交时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canReview" label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton link type="primary" @click="openDetail(row)">详情</ElButton>
              <ElButton
                v-permission="PERMISSION.blogArticleReview"
                link
                type="success"
                @click="openReview(row, 'APPROVED')"
              >
                通过
              </ElButton>
              <ElButton
                v-permission="PERMISSION.blogArticleReview"
                link
                type="danger"
                @click="openReview(row, 'REJECTED')"
              >
                驳回
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      :title="reviewing ? `审核文章：${reviewing.title}` : '审核文章'"
      :confirm-loading="submitting"
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
        <ElFormItem label="审核结果" prop="decision">
          <ElSelect v-model="decision">
            <ElOption
              v-for="item in REVIEW_DECISION"
              :key="item"
              :label="decisionLabel(item)"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="审核意见">
          <ElInput
            v-model="reviewComment"
            type="textarea"
            :rows="3"
            placeholder="可选，驳回时建议说明原因"
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
            <ElDescriptionsItem label="状态">
              <StatusTag :value="detail.status" />
            </ElDescriptionsItem>
            <ElDescriptionsItem label="审核状态">
              <StatusTag :value="detail.review_status" :labels="REVIEW_STATUS_LABEL" />
            </ElDescriptionsItem>
            <ElDescriptionsItem label="浏览">{{ formatNumber(detail.view_count) }}</ElDescriptionsItem>
            <ElDescriptionsItem label="提交时间">
              {{ formatDateTime(detail.created_at) }}
            </ElDescriptionsItem>
            <ElDescriptionsItem label="更新时间">
              {{ formatDateTime(detail.updated_at) }}
            </ElDescriptionsItem>
          </ElDescriptions>
          <h4 class="article-review-page__section-title">正文（纯文本）</h4>
          <pre class="article-review-page__content">{{ detail.content_markdown ?? '—' }}</pre>
        </template>
      </DataStateView>
    </ElDrawer>
  </div>
</template>

<style scoped>
.article-review-page__section-title {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 500;
}

.article-review-page__content {
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
