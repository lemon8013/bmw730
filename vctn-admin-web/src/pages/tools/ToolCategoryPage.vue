<script setup lang="ts">
/**
 * 工具分类：管理端的分类增删改查。
 *
 * 此前这里只有公开目录的只读展示 —— 后端不存在 `/admin/tool-categories` 写接口。
 * 现已补齐（`ToolCategoryCreateRequest` / `ToolCategoryUpdateRequest`，权限
 * `TOOL_CATEGORY_VIEW` / `TOOL_CATEGORY_EDIT`），本页因此恢复为可编辑列表：
 * 读走管理端接口（能看到 DISABLED 分类），写操作按按钮级权限控制。
 */
import { computed, reactive, ref } from 'vue'
import {
  ElButton,
  ElCard,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElSelect,
  ElSpace,
  ElTableColumn,
} from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

import {
  createToolCategory,
  deleteToolCategory,
  listAdminCategories,
  updateToolCategory,
} from '@/api/tools'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { useFieldPolicy } from '@/composables/useFieldPolicy'
import { PERMISSION } from '@/constants/permissions'
import type { ToolCategory, ToolCategoryUpdateRequest } from '@/types/tools'
import { renderError } from '@/utils/error'

const notify = useConfirm()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolCategoryView)

/** 按钮级权限不足时隐藏写操作入口。 */
const canEdit = true

/** 分类可选状态。 */
const CATEGORY_STATUS = ['ACTIVE', 'DISABLED'] as const
const STATUS_LABEL: Readonly<Record<string, string>> = {
  ACTIVE: '启用',
  DISABLED: '停用',
}

const { data, loading, failed, error, reload } = useAsyncData(() => listAdminCategories(true))

const rows = computed(() => (data.value ?? []) as unknown as Record<string, unknown>[])

// ---------------------------------------------------------------------------
// 新增 / 编辑
// ---------------------------------------------------------------------------

const dialogVisible = ref(false)
const submitting = ref(false)
const dialogError = ref('')
const formRef = ref<FormInstance>()
const editingId = ref<string | null>(null)

interface CategoryForm {
  category_code: string
  category_name: string
  description: string
  icon_url: string
  sort_order: number
  status: string
}

function emptyForm(): CategoryForm {
  return {
    category_code: '',
    category_name: '',
    description: '',
    icon_url: '',
    sort_order: 0,
    status: 'ACTIVE',
  }
}

const form = reactive<CategoryForm>(emptyForm())

const rules: FormRules<CategoryForm> = {
  category_code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }],
  category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, emptyForm())
  dialogError.value = ''
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>): void {
  const item = row as unknown as ToolCategory
  editingId.value = String(item.id)
  Object.assign(form, {
    category_code: item.category_code,
    category_name: item.category_name,
    description: item.description ?? '',
    icon_url: item.icon_url ?? '',
    sort_order: item.sort_order,
    status: item.status,
  })
  dialogError.value = ''
  dialogVisible.value = true
}

async function onSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  dialogError.value = ''
  try {
    if (editingId.value === null) {
      await createToolCategory({
        category_code: form.category_code.trim(),
        category_name: form.category_name.trim(),
        description: form.description.trim() === '' ? null : form.description.trim(),
        icon_url: form.icon_url.trim() === '' ? null : form.icon_url.trim(),
        sort_order: form.sort_order,
        status: form.status,
      })
      notify.success('分类已创建')
    } else {
      const payload: ToolCategoryUpdateRequest = {
        category_name: form.category_name.trim(),
        description: form.description.trim() === '' ? null : form.description.trim(),
        icon_url: form.icon_url.trim() === '' ? null : form.icon_url.trim(),
        sort_order: form.sort_order,
        status: form.status,
      }
      await updateToolCategory(editingId.value, payload)
      notify.success('分类已更新')
    }
    dialogVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught).message
  } finally {
    submitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 删除
// ---------------------------------------------------------------------------

async function onDelete(row: Record<string, unknown>): Promise<void> {
  const item = row as unknown as ToolCategory
  const confirmed = await notify.confirm({
    title: '删除工具分类',
    message: `确定删除「${item.category_name}」吗？删除后该分类不再出现在工具目录中。`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteToolCategory(String(item.id))
    notify.success('分类已删除')
    await reload()
  } catch (caught) {
    const rendered = renderError(caught)
    notify.failure(
      rendered.traceId === undefined
        ? rendered.message
        : `${rendered.message}（Trace ID: ${rendered.traceId}）`,
    )
  }
}
</script>

<template>
  <div class="tool-category-page">
    <PageHeader
      title="工具分类"
      description="维护工具的分类目录：新增、编辑、停用与删除，用于工具归类与展示排序。"
    >
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-permission="PERMISSION.toolCategoryEdit" type="primary" @click="openCreate">
          新增分类
        </ElButton>
      </template>
    </PageHeader>

    <ElCard shadow="never">
      <BaseTable
        :rows="rows"
        :loading="loading"
        :failed="failed"
        :error="error"
        :total="rows.length"
        :page="1"
        :page-size="rows.length || 1"
        :paginated="false"
        row-key="id"
        empty-text="暂无工具分类"
        @retry="reload"
      >
        <ElTableColumn
          v-if="!fields.isHidden('category_code')"
          prop="category_code"
          label="分类编码"
          min-width="160"
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
          min-width="240"
          show-overflow-tooltip
        />
        <ElTableColumn
          v-if="!fields.isHidden('icon_url')"
          prop="icon_url"
          label="图标地址"
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
        <ElTableColumn v-if="canEdit" label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <ElSpace>
              <ElButton
                v-permission="PERMISSION.toolCategoryEdit"
                link
                type="primary"
                @click="openEdit(row)"
              >
                编辑
              </ElButton>
              <ElButton
                v-permission="PERMISSION.toolCategoryEdit"
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

    <ElDialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增工具分类' : '编辑工具分类'"
      width="520px"
    >
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="96px">
        <ElFormItem label="分类编码" prop="category_code">
          <ElInput
            v-model="form.category_code"
            :disabled="editingId !== null"
            placeholder="如 json-tools"
          />
        </ElFormItem>
        <ElFormItem label="分类名称" prop="category_name">
          <ElInput v-model="form.category_name" maxlength="128" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="form.description" type="textarea" :rows="2" maxlength="500" />
        </ElFormItem>
        <ElFormItem label="图标地址">
          <ElInput v-model="form.icon_url" />
        </ElFormItem>
        <ElFormItem label="排序号">
          <ElInputNumber v-model="form.sort_order" :min="0" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="form.status" style="width: 160px">
            <ElOption
              v-for="item in CATEGORY_STATUS"
              :key="item"
              :label="STATUS_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <p v-if="dialogError !== ''" class="tool-category-page__error">{{ dialogError }}</p>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="onSubmit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.tool-category-page__error {
  margin: 8px 0 0;
  color: var(--el-color-danger);
  font-size: 13px;
}
</style>
