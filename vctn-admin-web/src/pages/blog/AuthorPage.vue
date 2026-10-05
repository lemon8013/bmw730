<script setup lang="ts">
/** 作者审核：作者列表与作者申请审核；审核操作需要 BLOG_AUTHOR_REVIEW 权限。 */
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

import { listAuthorApplications, listAuthors, reviewAuthorApplication } from '@/api/blog'
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
import type { AuthorApplication, AuthorApplicationReviewRequest } from '@/types/blog'
import {
  APPLICATION_STATUS,
  AUTHOR_STATUS,
  REVIEW_DECISION,
  STATUS_LABEL,
  type ReviewDecision,
} from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.blogAuthorReview)

/** 是否具备作者审核权限。 */
const canReview = computed(() => permission.has(PERMISSION.blogAuthorReview))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function statusLabel(value: string): string {
  return STATUS_LABEL[value] ?? value
}

/** 作者状态的中文标签。 */
const AUTHOR_STATUS_LABEL: Readonly<Record<string, string>> = {
  ACTIVE: '正常',
  SUSPENDED: '已暂停',
}

/** 作者申请状态的中文标签；PENDING 在审核语境下译为“待审核”。 */
const APPLICATION_STATUS_LABEL: Readonly<Record<string, string>> = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回',
}

// ---------------------------------------------------------------------------
// 作者列表
// ---------------------------------------------------------------------------

const authorStatus = ref('')

const {
  page: authorPage,
  pageSize: authorPageSize,
  total: authorTotal,
  applyPage: applyAuthorPage,
  changePage: changeAuthorPage,
  changePageSize: changeAuthorPageSize,
} = usePagination()

const {
  data: authors,
  loading: authorsLoading,
  failed: authorsFailed,
  error: authorsError,
  reload: reloadAuthors,
} = useAsyncData(() =>
  listAuthors({
    status: authorStatus.value === '' ? undefined : authorStatus.value,
    page: authorPage.value,
    page_size: authorPageSize.value,
  }),
)

watch(authors, (value) => {
  if (value) {
    applyAuthorPage(value)
  }
})

const authorRows = computed(() => asRows(authors.value?.items ?? []))

function onAuthorPageChange(next: number): void {
  changeAuthorPage(next)
  void reloadAuthors()
}

function onAuthorPageSizeChange(next: number): void {
  changeAuthorPageSize(next)
  void reloadAuthors()
}

function onAuthorSearch(): void {
  changeAuthorPage(1)
  void reloadAuthors()
}

// ---------------------------------------------------------------------------
// 作者申请
// ---------------------------------------------------------------------------

const applicationStatus = ref('')

const {
  page: applicationPage,
  pageSize: applicationPageSize,
  total: applicationTotal,
  applyPage: applyApplicationPage,
  changePage: changeApplicationPage,
  changePageSize: changeApplicationPageSize,
} = usePagination()

const {
  data: applications,
  loading: applicationsLoading,
  failed: applicationsFailed,
  error: applicationsError,
  reload: reloadApplications,
} = useAsyncData(() =>
  listAuthorApplications({
    status: applicationStatus.value === '' ? undefined : applicationStatus.value,
    page: applicationPage.value,
    page_size: applicationPageSize.value,
  }),
)

watch(applications, (value) => {
  if (value) {
    applyApplicationPage(value)
  }
})

const applicationRows = computed(() => asRows(applications.value?.items ?? []))

function onApplicationPageChange(next: number): void {
  changeApplicationPage(next)
  void reloadApplications()
}

function onApplicationPageSizeChange(next: number): void {
  changeApplicationPageSize(next)
  void reloadApplications()
}

function onApplicationSearch(): void {
  changeApplicationPage(1)
  void reloadApplications()
}

// ---------------------------------------------------------------------------
// 审核申请
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const reviewing = ref<AuthorApplication | null>(null)
const decision = ref<ReviewDecision>('APPROVED')
const reviewReason = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

const rules: FormRules = {
  decision: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
}

const formModel = computed(() => ({
  decision: decision.value,
  review_reason: reviewReason.value,
}))

function openReview(row: Record<string, unknown>, preset: ReviewDecision): void {
  reviewing.value = row as unknown as AuthorApplication
  decision.value = preset
  reviewReason.value = ''
  submitError.value = null
  submitTrace.value = null
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  const application = reviewing.value
  if (application === null) {
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
    const reason = reviewReason.value.trim()
    const payload: AuthorApplicationReviewRequest = {
      decision: decision.value,
      review_reason: reason === '' ? null : reason,
    }
    await reviewAuthorApplication(application.id, payload)
    notify.success(decision.value === 'APPROVED' ? '申请已通过' : '申请已驳回')
    dialogVisible.value = false
    await reloadApplications()
    await reloadAuthors()
  } catch (caught) {
    const rendered = renderError(caught)
    submitError.value = rendered.message
    submitTrace.value = rendered.traceId ?? null
  } finally {
    submitting.value = false
  }
}

function reloadAll(): void {
  void reloadAuthors()
  void reloadApplications()
}

/** 申请处于待处理状态时才允许审核。 */
function canReviewApplication(row: Record<string, unknown>): boolean {
  const application = row as unknown as AuthorApplication
  return application.status === 'PENDING'
}
</script>

<template>
  <div class="author-page">
    <PageHeader title="作者审核" description="查看作者列表并处理作者申请；审核需要 BLOG_AUTHOR_REVIEW 权限。">
      <template #actions>
        <ElButton @click="reloadAll">刷新</ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="author-page__section">
      <template #header>作者列表</template>
      <ElSpace wrap class="author-page__filters">
        <ElSelect v-model="authorStatus" placeholder="状态" clearable style="width: 160px">
          <ElOption
            v-for="item in AUTHOR_STATUS"
            :key="item"
            :label="statusLabel(item)"
            :value="item"
          />
        </ElSelect>
        <ElButton type="primary" @click="onAuthorSearch">查询</ElButton>
      </ElSpace>

      <BaseTable
        :rows="authorRows"
        :loading="authorsLoading"
        :failed="authorsFailed"
        :error="authorsError"
        :total="authorTotal"
        :page="authorPage"
        :page-size="authorPageSize"
        empty-text="暂无作者"
        @retry="reloadAuthors"
        @update:page="onAuthorPageChange"
        @update:page-size="onAuthorPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('author_name')"
          prop="author_name"
          label="作者名称"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('user_id')"
          prop="user_id"
          label="用户 ID"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('bio')"
          prop="bio"
          label="简介"
          min-width="220"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" :labels="AUTHOR_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('approved_at')" label="通过时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.approved_at) }}</template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <ElCard shadow="never" class="author-page__section">
      <template #header>作者申请</template>
      <ElSpace wrap class="author-page__filters">
        <ElSelect v-model="applicationStatus" placeholder="状态" clearable style="width: 160px">
          <ElOption
            v-for="item in APPLICATION_STATUS"
            :key="item"
            :label="statusLabel(item)"
            :value="item"
          />
        </ElSelect>
        <ElButton type="primary" @click="onApplicationSearch">查询</ElButton>
      </ElSpace>

      <BaseTable
        :rows="applicationRows"
        :loading="applicationsLoading"
        :failed="applicationsFailed"
        :error="applicationsError"
        :total="applicationTotal"
        :page="applicationPage"
        :page-size="applicationPageSize"
        empty-text="暂无作者申请"
        @retry="reloadApplications"
        @update:page="onApplicationPageChange"
        @update:page-size="onApplicationPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('user_id')"
          prop="user_id"
          label="用户 ID"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('application_reason')"
          prop="application_reason"
          label="申请理由"
          min-width="240"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" :labels="APPLICATION_STATUS_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('review_reason')"
          prop="review_reason"
          label="审核意见"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn v-if="!fields.isHidden('applied_at')" label="申请时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.applied_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canReview" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton
                v-permission="PERMISSION.blogAuthorReview"
                link
                type="success"
                :disabled="!canReviewApplication(row)"
                @click="openReview(row, 'APPROVED')"
              >
                通过
              </ElButton>
              <ElButton
                v-permission="PERMISSION.blogAuthorReview"
                link
                type="danger"
                :disabled="!canReviewApplication(row)"
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
      :title="reviewing ? `审核申请：用户 ${reviewing.user_id}` : '审核申请'"
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
              :label="statusLabel(item)"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="审核意见">
          <ElInput
            v-model="reviewReason"
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
.author-page__section {
  margin-bottom: 16px;
}

.author-page__filters {
  margin-bottom: 12px;
}
</style>
