<script setup lang="ts">
/**
 * 评论审核：默认展示待审核评论；填入文章 ID 后切换为查看该文章的评论。
 * 审核与删除操作需要 BLOG_COMMENT_REVIEW 权限。
 */
import { computed, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import {
  deleteComment,
  listComments,
  listPendingComments,
  reviewComment,
} from '@/api/blog'
import PageHeader from '@/components/common/PageHeader.vue'
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
import type { Comment, CommentReviewRequest } from '@/types/blog'
import { REVIEW_DECISION, STATUS_LABEL, type ReviewDecision } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.blogCommentReview)

/** 是否具备评论审核权限。 */
const canReview = computed(() => permission.has(PERMISSION.blogCommentReview))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function decisionLabel(decision: string): string {
  return STATUS_LABEL[decision] ?? decision
}

/** 评论状态的中文标签；PENDING 在审核语境下译为“待审核”。 */
const COMMENT_STATUS_LABEL: Readonly<Record<string, string>> = {
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

const articleId = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() => {
  const id = articleId.value.trim()
  if (id === '') {
    return listPendingComments(page.value, pageSize.value)
  }
  return listComments(id, page.value, pageSize.value)
})

watch(data, (value) => {
  if (value) {
    applyPage(value)
  }
})

const rows = computed(() => asRows(data.value?.items ?? []))

/** 当前是否为文章评论视图。 */
const isArticleMode = computed(() => articleId.value.trim() !== '')

function onSearch(): void {
  changePage(1)
  void reload()
}

function onReset(): void {
  articleId.value = ''
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
// 审核对话框
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const reviewing = ref<Comment | null>(null)
const decision = ref<ReviewDecision>('APPROVED')
const reviewCommentText = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

const rules: FormRules = {
  decision: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
}

const formModel = computed(() => ({
  decision: decision.value,
  review_comment: reviewCommentText.value,
}))

function openReview(row: Record<string, unknown>, preset: ReviewDecision): void {
  reviewing.value = row as unknown as Comment
  decision.value = preset
  reviewCommentText.value = ''
  submitError.value = null
  submitTrace.value = null
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  const comment = reviewing.value
  if (comment === null) {
    return
  }
  const valid = await formRef.value?.validate()
  if (valid !== true) {
    return
  }
  submitError.value = null
  submitTrace.value = null
  submitting.value = true
  try {
    const commentText = reviewCommentText.value.trim()
    const payload: CommentReviewRequest = {
      decision: decision.value,
      review_comment: commentText === '' ? null : commentText,
    }
    await reviewComment(comment.id, payload)
    notify.success(decision.value === 'APPROVED' ? '评论已通过' : '评论已驳回')
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

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const comment = row as unknown as Comment
  const confirmed = await notify.confirm({
    title: '删除评论',
    message: '确定要删除该评论吗？该操作不可撤销。',
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteComment(comment.id)
    notify.success('评论已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="comment-review-page">
    <PageHeader
      title="评论审核"
      description="默认展示待审核评论；填入文章 ID 可查看该文章的全部评论。审核需要 BLOG_COMMENT_REVIEW 权限。"
    >
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="comment-review-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="articleId"
          placeholder="按文章 ID 筛选"
          clearable
          style="width: 240px"
          @keyup.enter="onSearch"
        />
        <ElButton type="primary" @click="onSearch">查询</ElButton>
        <ElButton @click="onReset">重置</ElButton>
      </ElSpace>
      <p class="comment-review-page__hint">
        {{ isArticleMode ? '当前视图：指定文章的评论' : '当前视图：待审核评论' }}
      </p>
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
        :empty-text="isArticleMode ? '该文章暂无评论' : '暂无待审核评论'"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn v-if="!fields.isHidden('article_id')" prop="article_id" label="文章 ID" min-width="150" />
        <ElTableColumn v-if="!fields.isHidden('user_id')" prop="user_id" label="用户 ID" min-width="150" />
        <ElTableColumn
          v-if="!fields.isHidden('content')"
          prop="content"
          label="评论内容"
          min-width="260"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" :labels="COMMENT_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('created_at')" label="提交时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canReview" label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton
                v-permission="PERMISSION.blogCommentReview"
                link
                type="success"
                @click="openReview(row, 'APPROVED')"
              >
                通过
              </ElButton>
              <ElButton
                v-permission="PERMISSION.blogCommentReview"
                link
                type="danger"
                @click="openReview(row, 'REJECTED')"
              >
                驳回
              </ElButton>
              <ElButton
                v-permission="PERMISSION.blogCommentReview"
                link
                type="danger"
                @click="onDelete(row)"
              >
                删除
              </ElButton>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <BaseDialog
      v-model="dialogVisible"
      title="审核评论"
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
        <ElFormItem label="评论内容">
          <pre class="comment-review-page__content">{{ reviewing?.content ?? '—' }}</pre>
        </ElFormItem>
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
            v-model="reviewCommentText"
            type="textarea"
            :rows="3"
            placeholder="可选，驳回时建议说明原因"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.comment-review-page__filters {
  margin-bottom: 16px;
}

.comment-review-page__hint {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.comment-review-page__content {
  max-height: 200px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background-color: var(--el-fill-color-light);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
