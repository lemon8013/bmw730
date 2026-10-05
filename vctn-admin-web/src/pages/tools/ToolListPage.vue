<script setup lang="ts">
/** 工具管理：工具的新建、编辑与状态流转。 */
import { computed, reactive, ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElCard,
  ElCol,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElRow,
  ElSelect,
  ElSpace,
  ElTableColumn,
  type FormRules,
} from 'element-plus'

import { listCategories } from '@/api/catalog'
import {
  createTool,
  listAdminTools,
  listToolVisibility,
  setToolStatus,
  setToolVisibility,
  updateTool,
} from '@/api/tools'
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
import type { Tool, ToolCreateRequest, ToolUpdateRequest } from '@/types/tools'
import {
  STATUS_LABEL,
  TOOL_EXECUTION_MODE,
  TOOL_MODE_LABEL,
  TOOL_STATUS,
  TOOL_VISIBILITY,
  TOOL_VISIBILITY_LABEL,
  type ToolVisibilityLevel,
} from '@/types/enums'
import { renderError, type RenderedError } from '@/utils/error'

const notify = useConfirm()
const permission = usePermissionStore()
/** 字段级权限：控制每个字段的可见 / 只读 / 可编辑。 */
const fields = useFieldPolicy(PERMISSION.toolView)
/** 是否具备工具编辑权限。 */
const canEdit = permission.has(PERMISSION.toolEdit)
/** 可见性开关写入的是访问策略，受独立的策略管理权限控制。 */
const canManageVisibility = permission.has(PERMISSION.toolAccessManage)

/** BaseTable 接收结构化行；接口 DTO 在此边界转换为行记录。 */
function asRows(items: readonly unknown[]): Record<string, unknown>[] {
  return items as unknown as Record<string, unknown>[]
}

function toTool(row: Record<string, unknown>): Tool {
  return row as unknown as Tool
}

/** 动作类失败的提示文案，附带 Trace ID 便于排查。 */
function failureText(caught: unknown): string {
  const rendered = renderError(caught)
  return rendered.traceId === undefined
    ? rendered.message
    : `${rendered.message}（Trace ID: ${rendered.traceId}）`
}

// ---------------------------------------------------------------------------
// 分类
// ---------------------------------------------------------------------------

const { data: categories } = useAsyncData(() => listCategories())

const categoryOptions = computed(() => categories.value ?? [])

const categoryNameById = computed(() => {
  const map = new Map<string, string>()
  for (const category of categoryOptions.value) {
    map.set(String(category.id), category.category_name)
  }
  return map
})

function categoryNameOf(row: Record<string, unknown>): string {
  const id = row.category_id
  if (id === null || id === undefined || id === '') {
    return '—'
  }
  return categoryNameById.value.get(String(id)) ?? String(id)
}

/**
 * 表单中的分类保存为字符串；ToolCreateRequest / ToolUpdateRequest 的分类字段
 * 被后端冻结为 number，仅在提交边界做一次转换。
 */
function categoryIdPayload(value: string): number | null {
  if (value === '') {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

// ---------------------------------------------------------------------------
// 列表与筛选
// ---------------------------------------------------------------------------

const filters = reactive<{
  status: string
  category_id: string
  keyword: string
}>({ status: '', category_id: '', keyword: '' })

const { page, pageSize, total, applyPage, changePage, changePageSize } = usePagination()

const { data, loading, failed, error, reload } = useAsyncData(() =>
  listAdminTools({
    status: filters.status === '' ? undefined : filters.status,
    category_id: filters.category_id === '' ? undefined : filters.category_id,
    keyword: filters.keyword.trim() === '' ? undefined : filters.keyword.trim(),
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

function onPageChange(next: number): void {
  changePage(next)
  void reload()
}

function onPageSizeChange(next: number): void {
  changePageSize(next)
  void reload()
}

function search(): void {
  changePage(1)
  void reload()
}

function resetFilters(): void {
  filters.status = ''
  filters.category_id = ''
  filters.keyword = ''
  search()
}

// ---------------------------------------------------------------------------
// 表单
// ---------------------------------------------------------------------------

type ToolFormModel = {
  code: string
  name: string
  slug: string
  component_key: string
  execution_mode: string
  category_id: string
  icon: string
  summary: string
  description: string
  keywords: string[]
  tags: string[]
  status: string
  sort_order: number
}

function emptyForm(): ToolFormModel {
  return {
    code: '',
    name: '',
    slug: '',
    component_key: '',
    execution_mode: 'FRONTEND',
    category_id: '',
    icon: '',
    summary: '',
    description: '',
    keywords: [],
    tags: [],
    status: 'DRAFT',
    sort_order: 0,
  }
}

const formRules: FormRules = {
  code: [{ required: true, message: '请输入工具 code', trigger: 'blur' }],
  name: [{ required: true, message: '请输入工具名称', trigger: 'blur' }],
  slug: [{ required: true, message: '请输入 slug', trigger: 'blur' }],
  component_key: [{ required: true, message: '请输入 component_key', trigger: 'blur' }],
  execution_mode: [{ required: true, message: '请选择执行方式', trigger: 'change' }],
}

const dialogError = ref<RenderedError | null>(null)
const createModel = reactive<ToolFormModel>(emptyForm())
const createFormRef = ref<InstanceType<typeof BaseForm>>()
const createRules: FormRules = formRules
const editRules: FormRules = formRules

function toMessages(): { message: string | null; traceId: string | null } {
  return {
    message: dialogError.value?.message ?? null,
    traceId: dialogError.value?.traceId ?? null,
  }
}

// ---------------------------------------------------------------------------
// 新建工具
// ---------------------------------------------------------------------------

const createVisible = ref(false)
const createSubmitting = ref(false)

function openCreate(): void {
  Object.assign(createModel, emptyForm())
  dialogError.value = null
  createVisible.value = true
}

async function submitCreate(): Promise<void> {
  const valid = await createFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  dialogError.value = null
  createSubmitting.value = true
  try {
    const payload: ToolCreateRequest = {
      code: createModel.code.trim(),
      name: createModel.name.trim(),
      slug: createModel.slug.trim(),
      component_key: createModel.component_key.trim(),
      execution_mode: createModel.execution_mode,
      category_id: categoryIdPayload(createModel.category_id),
      icon: createModel.icon.trim() === '' ? null : createModel.icon.trim(),
      summary: createModel.summary.trim() === '' ? null : createModel.summary.trim(),
      description: createModel.description.trim() === '' ? null : createModel.description.trim(),
      keywords: [...createModel.keywords],
      tags: [...createModel.tags],
      status: createModel.status,
      sort_order: createModel.sort_order,
    }
    await createTool(payload)
    notify.success('工具已创建')
    createVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    createSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 编辑工具
// ---------------------------------------------------------------------------

const editVisible = ref(false)
const editSubmitting = ref(false)
const activeTool = ref<Tool | null>(null)
const editModel = reactive<ToolFormModel>(emptyForm())
const editFormRef = ref<InstanceType<typeof BaseForm>>()

function openEdit(row: Record<string, unknown>): void {
  const tool = toTool(row)
  activeTool.value = tool
  Object.assign(editModel, {
    code: tool.code,
    name: tool.name,
    slug: tool.slug,
    component_key: tool.component_key,
    execution_mode: tool.execution_mode,
    category_id:
      tool.category_id === null || tool.category_id === undefined
        ? ''
        : String(tool.category_id),
    icon: tool.icon ?? '',
    summary: tool.summary ?? '',
    description: tool.description ?? '',
    keywords: tool.keywords ? [...tool.keywords] : [],
    tags: tool.tags ? [...tool.tags] : [],
    status: tool.status,
    sort_order: tool.sort_order,
  })
  dialogError.value = null
  editVisible.value = true
}

async function submitEdit(): Promise<void> {
  const tool = activeTool.value
  if (tool === null) {
    return
  }
  const valid = await editFormRef.value?.validate()
  if (valid !== true) {
    return
  }
  dialogError.value = null
  editSubmitting.value = true
  try {
    const payload: ToolUpdateRequest = {
      code: editModel.code.trim(),
      name: editModel.name.trim(),
      slug: editModel.slug.trim(),
      component_key: editModel.component_key.trim(),
      execution_mode: editModel.execution_mode,
      category_id: categoryIdPayload(editModel.category_id),
      icon: editModel.icon.trim() === '' ? null : editModel.icon.trim(),
      summary: editModel.summary.trim() === '' ? null : editModel.summary.trim(),
      description: editModel.description.trim() === '' ? null : editModel.description.trim(),
      keywords: [...editModel.keywords],
      tags: [...editModel.tags],
      status: editModel.status,
      sort_order: editModel.sort_order,
    }
    await updateTool(tool.id, payload)
    notify.success('工具已更新')
    editVisible.value = false
    await reload()
  } catch (caught) {
    dialogError.value = renderError(caught)
  } finally {
    editSubmitting.value = false
  }
}

// ---------------------------------------------------------------------------
// 可见性（所有人可用 / 注册用户可用）
// ---------------------------------------------------------------------------

const {
  data: visibilityRows,
  reload: reloadVisibility,
} = useAsyncData(() => listToolVisibility())

const visibilityByTool = computed(() => {
  const map = new Map<string, string>()
  for (const row of visibilityRows.value ?? []) {
    map.set(String(row.tool_id), row.visibility)
  }
  return map
})

/** 尚未取到可见性时返回空串，由单元格渲染为占位符。 */
function visibilityOf(row: Record<string, unknown>): string {
  return visibilityByTool.value.get(String(row.id)) ?? ''
}

const savingVisibilityId = ref<string>('')

async function onChangeVisibility(row: Record<string, unknown>, value: string): Promise<void> {
  const tool = toTool(row)
  savingVisibilityId.value = String(tool.id)
  try {
    await setToolVisibility(tool.id, { visibility: value })
    notify.success(`已设为「${TOOL_VISIBILITY_LABEL[value as ToolVisibilityLevel] ?? value}」`)
  } catch (caught) {
    notify.failure(failureText(caught))
  } finally {
    // The spinner is driven solely by `savingVisibilityId`: without this reset
    // the select stays in its loading state forever after the first change.
    await reloadVisibility()
    savingVisibilityId.value = ''
  }
}

// ---------------------------------------------------------------------------
// 状态流转
// ---------------------------------------------------------------------------

async function onSetStatus(row: Record<string, unknown>, status: string): Promise<void> {
  const tool = toTool(row)
  if (tool.status === status) {
    return
  }
  const confirmed = await notify.confirm({
    title: '变更工具状态',
    message: `确定将「${tool.name}」的状态从 ${tool.status} 变更为 ${status} 吗？`,
    danger: true,
  })
  if (!confirmed) {
    return
  }
  try {
    await setToolStatus(tool.id, { status })
    notify.success('工具状态已更新')
    await reload()
  } catch (caught) {
    notify.failure(failureText(caught))
  }
}
</script>

<template>
  <div class="tool-list-page">
    <PageHeader title="工具管理" description="管理工具元数据、组件绑定与上下线状态。">
      <template #actions>
        <ElButton @click="reload">刷新</ElButton>
        <ElButton v-if="canEdit" type="primary" @click="openCreate">新建工具</ElButton>
      </template>
    </PageHeader>

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="tool-list-page__notice"
      title="关于“发布”"
      description="后端仅提供 PUT /admin/tools/{id}/status 状态变更接口，未提供独立的“发布”接口；本页通过状态流转（ACTIVE / DRAFT / OFFLINE / DEPRECATED）管理工具的可用性。"
    />

    <ElAlert
      type="info"
      :closable="false"
      show-icon
      class="tool-list-page__notice"
      title="关于“可见性”"
      description="可见性决定谁可以使用工具：所有人可用（访客与登录用户均可）与注册用户可用（仅登录用户）。它写入 tool_access_policy 的 GUEST / USER 两行策略；该表没有 subject_id 列，因此无法指定到某个具体用户。工具的 status 仍是总开关：非 ACTIVE 的工具对所有人立即可见性失效。"
    />

    <ElCard shadow="never" class="tool-list-page__filters">
      <ElRow :gutter="12">
        <ElCol :xs="24" :sm="8" :md="6">
          <ElInput
            v-model="filters.keyword"
            placeholder="工具名称 / code"
            clearable
            @keyup.enter="search"
          />
        </ElCol>
        <ElCol :xs="24" :sm="8" :md="6">
          <ElSelect v-model="filters.category_id" placeholder="分类" clearable style="width: 100%">
            <ElOption
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.category_name"
              :value="String(item.id)"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :sm="8" :md="6">
          <ElSelect v-model="filters.status" placeholder="状态" clearable style="width: 100%">
            <ElOption
              v-for="item in TOOL_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElCol>
        <ElCol :xs="24" :md="6">
          <ElSpace>
            <ElButton type="primary" @click="search">查询</ElButton>
            <ElButton @click="resetFilters">重置</ElButton>
          </ElSpace>
        </ElCol>
      </ElRow>
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
        empty-text="暂无工具"
        @retry="reload"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      >
        <ElTableColumn v-if="!fields.isHidden('code')" prop="code" label="Code" min-width="140" />
        <ElTableColumn v-if="!fields.isHidden('name')" prop="name" label="名称" min-width="140" />
        <ElTableColumn v-if="!fields.isHidden('slug')" prop="slug" label="Slug" min-width="140" />
        <ElTableColumn v-if="!fields.isHidden('category_id')" label="分类" min-width="120">
          <template #default="{ row }">{{ categoryNameOf(row) }}</template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('component_key')"
          prop="component_key"
          label="组件 key"
          min-width="180"
        />
        <ElTableColumn
          v-if="!fields.isHidden('execution_mode')"
          prop="execution_mode"
          label="执行方式"
          width="120"
        >
          <template #default="{ row }">
            <StatusTag :value="row.execution_mode" :labels="TOOL_MODE_LABEL" />
          </template>
        </ElTableColumn>
        <ElTableColumn v-if="!fields.isHidden('status')" prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.status" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="可见性" width="170">
          <template #default="{ row }">
            <ElSelect
              v-if="canManageVisibility && visibilityOf(row) !== ''"
              :model-value="visibilityOf(row)"
              size="small"
              style="width: 140px"
              :loading="savingVisibilityId === String(row.id)"
              @change="(value: string) => onChangeVisibility(row, value)"
            >
              <ElOption
                v-for="item in TOOL_VISIBILITY"
                :key="item"
                :label="TOOL_VISIBILITY_LABEL[item]"
                :value="item"
              />
            </ElSelect>
            <StatusTag
              v-else-if="visibilityOf(row) !== ''"
              :value="visibilityOf(row)"
              :labels="TOOL_VISIBILITY_LABEL"
            />
            <span v-else>—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn
          v-if="!fields.isHidden('sort_order')"
          prop="sort_order"
          label="排序"
          width="90"
        />
        <ElTableColumn v-if="canEdit" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <ElSpace>
              <ElButton v-permission="PERMISSION.toolEdit" link type="primary" @click="openEdit(row)">
                编辑
              </ElButton>
              <ElDropdown @command="(command) => onSetStatus(row, String(command))">
                <ElButton v-permission="PERMISSION.toolEdit" link type="primary">状态变更</ElButton>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem
                      v-for="item in TOOL_STATUS"
                      :key="item"
                      :command="item"
                      :disabled="item === row.status"
                    >
                      {{ STATUS_LABEL[item] ?? item }}
                    </ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </ElSpace>
          </template>
        </ElTableColumn>
      </BaseTable>
    </ElCard>

    <!-- 新建工具 -->
    <BaseDialog
      v-model="createVisible"
      title="新建工具"
      width="720px"
      :confirm-loading="createSubmitting"
      @confirm="submitCreate"
    >
      <BaseForm
        ref="createFormRef"
        :model="createModel"
        :rules="createRules"
        :error-message="toMessages().message"
        :error-trace-id="toMessages().traceId"
        hide-footer
      >
        <ElFormItem v-if="!fields.isHidden('code')" label="Code" prop="code">
          <ElInput
            v-model="createModel.code"
            :disabled="fields.isReadOnly('code')"
            placeholder="唯一标识，例如 calculator"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('name')" label="名称" prop="name">
          <ElInput v-model="createModel.name" :disabled="fields.isReadOnly('name')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('slug')" label="Slug" prop="slug">
          <ElInput
            v-model="createModel.slug"
            :disabled="fields.isReadOnly('slug')"
            placeholder="URL 友好标识"
          />
        </ElFormItem>
        <ElFormItem label="组件 key" prop="component_key">
          <ElInput
            v-model="createModel.component_key"
            :disabled="fields.isReadOnly('component_key')"
            placeholder="例如 tool.calculator"
          />
          <p class="tool-list-page__hint">
            必须与已注册的 tool_component_registry.component_key 完全一致，前端将据此定位渲染组件；未注册的 key 会导致工具无法执行。
          </p>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('execution_mode')" label="执行方式" prop="execution_mode">
          <ElSelect
            v-model="createModel.execution_mode"
            :disabled="fields.isReadOnly('execution_mode')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in TOOL_EXECUTION_MODE"
              :key="item"
              :label="TOOL_MODE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('category_id')" label="分类">
          <ElSelect
            v-model="createModel.category_id"
            clearable
            :disabled="fields.isReadOnly('category_id')"
            placeholder="请选择分类"
            style="width: 100%"
          >
            <ElOption
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.category_name"
              :value="String(item.id)"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('icon')" label="图标">
          <ElInput v-model="createModel.icon" :disabled="fields.isReadOnly('icon')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('summary')" label="摘要">
          <ElInput v-model="createModel.summary" :disabled="fields.isReadOnly('summary')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="createModel.description"
            type="textarea"
            :rows="3"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('keywords')" label="关键字">
          <ElSelect
            v-model="createModel.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            :disabled="fields.isReadOnly('keywords')"
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('tags')" label="标签">
          <ElSelect
            v-model="createModel.tags"
            multiple
            filterable
            allow-create
            default-first-option
            :disabled="fields.isReadOnly('tags')"
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('status')" label="状态">
          <ElSelect
            v-model="createModel.status"
            :disabled="fields.isReadOnly('status')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in TOOL_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('sort_order')" label="排序">
          <ElInputNumber
            v-model="createModel.sort_order"
            :min="0"
            :disabled="fields.isReadOnly('sort_order')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>

    <!-- 编辑工具 -->
    <BaseDialog
      v-model="editVisible"
      :title="activeTool ? `编辑工具：${activeTool.name}` : '编辑工具'"
      width="720px"
      :confirm-loading="editSubmitting"
      @confirm="submitEdit"
    >
      <BaseForm
        ref="editFormRef"
        :model="editModel"
        :rules="editRules"
        :error-message="toMessages().message"
        :error-trace-id="toMessages().traceId"
        hide-footer
      >
        <ElFormItem label="Code" prop="code">
          <ElInput
            v-model="editModel.code"
            :disabled="fields.isReadOnly('code')"
            placeholder="唯一标识"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('name')" label="名称" prop="name">
          <ElInput v-model="editModel.name" :disabled="fields.isReadOnly('name')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('slug')" label="Slug" prop="slug">
          <ElInput v-model="editModel.slug" :disabled="fields.isReadOnly('slug')" />
        </ElFormItem>
        <ElFormItem label="组件 key" prop="component_key">
          <ElInput
            v-model="editModel.component_key"
            :disabled="fields.isReadOnly('component_key')"
          />
          <p class="tool-list-page__hint">
            必须与已注册的 tool_component_registry.component_key 完全一致，未注册的 key 会导致工具无法执行。
          </p>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('execution_mode')" label="执行方式" prop="execution_mode">
          <ElSelect
            v-model="editModel.execution_mode"
            :disabled="fields.isReadOnly('execution_mode')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in TOOL_EXECUTION_MODE"
              :key="item"
              :label="TOOL_MODE_LABEL[item]"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('category_id')" label="分类">
          <ElSelect
            v-model="editModel.category_id"
            clearable
            :disabled="fields.isReadOnly('category_id')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in categoryOptions"
              :key="item.id"
              :label="item.category_name"
              :value="String(item.id)"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('icon')" label="图标">
          <ElInput v-model="editModel.icon" :disabled="fields.isReadOnly('icon')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('summary')" label="摘要">
          <ElInput v-model="editModel.summary" :disabled="fields.isReadOnly('summary')" />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('description')" label="描述">
          <ElInput
            v-model="editModel.description"
            type="textarea"
            :rows="3"
            :disabled="fields.isReadOnly('description')"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('keywords')" label="关键字">
          <ElSelect
            v-model="editModel.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            :disabled="fields.isReadOnly('keywords')"
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('tags')" label="标签">
          <ElSelect
            v-model="editModel.tags"
            multiple
            filterable
            allow-create
            default-first-option
            :disabled="fields.isReadOnly('tags')"
            placeholder="输入后回车添加"
            style="width: 100%"
          />
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('status')" label="状态">
          <ElSelect
            v-model="editModel.status"
            :disabled="fields.isReadOnly('status')"
            style="width: 100%"
          >
            <ElOption
              v-for="item in TOOL_STATUS"
              :key="item"
              :label="STATUS_LABEL[item] ?? item"
              :value="item"
            />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="!fields.isHidden('sort_order')" label="排序">
          <ElInputNumber
            v-model="editModel.sort_order"
            :min="0"
            :disabled="fields.isReadOnly('sort_order')"
          />
        </ElFormItem>
      </BaseForm>
    </BaseDialog>
  </div>
</template>

<style scoped>
.tool-list-page__notice {
  margin-bottom: 16px;
}

.tool-list-page__filters {
  margin-bottom: 16px;
}

.tool-list-page__hint {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
