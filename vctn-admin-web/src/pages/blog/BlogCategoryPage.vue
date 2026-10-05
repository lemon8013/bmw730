<script setup lang="ts">
/** 博客分类：分类的查询与增删改，写操作受 BLOG_CATEGORY_MANAGE 约束。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElCard,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import { createCategory, deleteCategory, listCategories, updateCategory } from '@/api/blog'
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
import type { BlogCategory, CategoryCreateRequest, CategoryUpdateRequest } from '@/types/blog'
import { ACTIVE_STATUS, STATUS_LABEL } from '@/types/enums'
import { renderError } from '@/utils/error'
import { formatDateTime } from '@/utils/format'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.blogCategoryManage)

/** 是否具备分类写权限。 */
const canManage = computed(() => permission.has(PERMISSION.blogCategoryManage))

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function statusLabel(value: string): string {
  return STATUS_LABEL[value] ?? value
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
const status = ref('')

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listCategories({
    keyword: keyword.value.trim() === '' ? undefined : keyword.value.trim(),
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

function onSearch(): void {
  changePage(1)
  void reload()
}

function onReset(): void {
  keyword.value = ''
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

interface CategoryFormModel {
  category_code: string
  category_name: string
  description: string
  sort_order: number
  status: string
}

const formModel = reactive<CategoryFormModel>({
  category_code: '',
  category_name: '',
  description: '',
  sort_order: 0,
  status: 'ACTIVE',
})

const rules: FormRules = {
  category_code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }],
  category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const submitTrace = ref<string | null>(null)
const formRef = ref<InstanceType<typeof BaseForm>>()

function clearSubmitError(): void {
  submitError.value = null
  submitTrace.value = null
}

function openCreate(): void {
  editingId.value = null
  formModel.category_code = ''
  formModel.category_name = ''
  formModel.description = ''
  formModel.sort_order = 0
  formModel.status = 'ACTIVE'
  clearSubmitError()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const category = row as unknown as BlogCategory
  editingId.value = category.id
  formModel.category_code = category.category_code
  formModel.category_name = category.category_name
  formModel.description = category.description ?? ''
  formModel.sort_order = category.sort_order
  formModel.status = category.status
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
    const description = formModel.description.trim()
    if (editingId.value === null) {
      const payload: CategoryCreateRequest = {
        category_code: formModel.category_code,
        category_name: formModel.category_name,
        description: description === '' ? null : description,
        sort_order: formModel.sort_order,
      }
      await createCategory(payload)
      notify.success('分类已创建')
    } else {
      const payload: CategoryUpdateRequest = {
        category_name: formModel.category_name,
        description: description === '' ? null : description,
        sort_order: formModel.sort_order,
        status: formModel.status,
      }
      await updateCategory(editingId.value, payload)
      notify.success('分类已更新')
    }
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    reportSubmitError(caught)
  } finally {
    submitting.value = false
  }
}

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const category = row as unknown as BlogCategory
  const confirmed = await notify.confirm({
    title: '删除分类',
    message: `确定要删除分类「${category.category_name}」吗？该操作不可撤销。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteCategory(category.id)
    notify.success('分类已删除')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="blog-category-page">
    <PageHeader title="博客分类" description="维护文章分类；写操作需要 BLOG_CATEGORY_MANAGE 权限。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton
          v-permission="PERMISSION.blogCategoryManage"
          type="primary"
          @click="openCreate"
        >
          新建分类
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never" class="blog-category-page__filters">
      <ElSpace wrap>
        <ElInput
          v-model="keyword"
          placeholder="按名称 / 编码搜索"
          clearable
          style="width: 220px"
          @keyup.enter="onSearch"
        />
        <ElSelect v-model="status" placeholder="状态" clearable style="width: 140px">
          <ElOption
            v-for="item in ACTIVE_STATUS"
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
        empty-text="暂无分类"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn
          v-if="!fields.isHidden('category_code')"
          prop="category_code"
          label="分类编码"
          min-width="150"
        />
        <ElTableColumn
          v-if="!fields.isHidden('category_name')"
          prop="category_name"
          label="分类名称"
          min-width="160"
        />
        <ElTableColumn
          v-if="!fields.isHidden('description')"
          prop="description"
          label="描述"
          min-width="200"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('sort_order')"
          prop="sort_order"
          label="排序"
          width="90"
        />
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('updated_at')"
          label="更新时间"
          width="180"
        >
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canManage" label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <ElSpace wrap>
              <ElButton
                v-permission="PERMISSION.blogCategoryManage"
                link
                type="primary"
                @click="openEdit(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-permission="PERMISSION.blogCategoryManage"
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
      :title="editingId === null ? '新建分类' : '编辑分类'"
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
        <ElFormItem
          v-if="!fields.isHidden('category_code')"
          label="分类编码"
          prop="category_code"
        >
          <ElInput
            v-model="formModel.category_code"
            :disabled="editingId !== null || fields.isReadOnly('category_code')"
            placeholder="例如 NEWS"
          />
        </ElFormItem>
        <ElFormItem
          v-if="!fields.isHidden('category_name')"
          label="分类名称"
          prop="category_name"
        >
          <ElInput
            v-model="formModel.category_name"
            :disabled="fields.isReadOnly('category_name')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('sort_order')" label="排序">
          <ElInputNumber
            v-model="formModel.sort_order"
            :disabled="fields.isReadOnly('sort_order')"
          />
        </ElFormItem>
        <ElFormItem v-if="editingId !== null && !fields.isHidden('status')" label="状态">
          <ElSelect v-model="formModel.status" :disabled="fields.isReadOnly('status')">
            <ElOption
              v-for="item in ACTIVE_STATUS"
              :key="item"
              :label="statusLabel(item)"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="formModel.description"
            type="textarea"
            :rows="3"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.blog-category-page__filters {
  margin-bottom: 16px;
}
</style>
