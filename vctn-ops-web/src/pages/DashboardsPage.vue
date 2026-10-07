<script setup lang="ts">
/**
 * Dashboard configuration.
 *
 * A dashboard is a named container; what it shows lives in its widgets. Both
 * are managed here, and the widget list is opened from the dashboard it belongs
 * to so the editor never edits a widget without knowing its parent.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElDrawer,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElSwitch,
  ElTable,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'

import {
  createDashboard,
  createWidget,
  deleteDashboard,
  deleteWidget,
  listDashboards,
  listWidgets,
  updateDashboard,
} from '@/api/ops/dashboard'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { WIDGET_TYPE } from '@/types/enums'
import type { Dashboard } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.dashboardManage))

const keyword = ref('')

const list = usePagedList<Dashboard>((page, pageSize) =>
  listDashboards(page, pageSize, keyword.value.trim() === '' ? undefined : keyword.value.trim()),
)

void list.reload()

/* ---------- dashboard dialog ---------- */

const editing = ref<Dashboard | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface DashboardForm {
  dashboard_code: string
  name: string
  description: string
  is_default: boolean
}

const form = ref<DashboardForm>({
  dashboard_code: '',
  name: '',
  description: '',
  is_default: false,
})

const rules: FormRules<DashboardForm> = {
  dashboard_code: [{ required: true, message: '请输入仪表盘编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

function openCreate(): void {
  editing.value = null
  form.value = { dashboard_code: '', name: '', description: '', is_default: false }
  dialogVisible.value = true
}

function openEdit(row: Dashboard): void {
  editing.value = row
  form.value = {
    dashboard_code: row.dashboard_code,
    name: row.name,
    description: row.description ?? '',
    is_default: row.is_default,
  }
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  const instance = formRef.value
  if (instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    if (editing.value === null) {
      await createDashboard({
        dashboard_code: form.value.dashboard_code.trim(),
        name: form.value.name.trim(),
        description: form.value.description.trim() === '' ? null : form.value.description.trim(),
        is_default: form.value.is_default,
      })
      ElMessage.success('仪表盘已创建')
    } else {
      await updateDashboard(editing.value.id, {
        name: form.value.name.trim(),
        description: form.value.description.trim() === '' ? null : form.value.description.trim(),
        is_default: form.value.is_default,
      })
      ElMessage.success('仪表盘已更新')
    }
    dialogVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function remove(row: Dashboard): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除仪表盘',
    message: `确定删除仪表盘「${row.name}」？其下所有组件一并删除。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteDashboard(row.id)
    ElMessage.success('仪表盘已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

/* ---------- widgets ---------- */

const widgetOwner = ref<Dashboard | null>(null)
const widgetDrawerVisible = ref(false)
const widgets = useAsyncData(() =>
  widgetOwner.value === null ? Promise.resolve(null) : listWidgets(widgetOwner.value.id),
)

const widgetRows = computed(() => widgets.data.value ?? [])

const widgetDialogVisible = ref(false)
const widgetFormRef = ref<FormInstance>()
const widgetForm = ref({
  widget_type: 'STAT',
  title: '',
  metric_key: '',
  width: 6,
  height: 4,
})
const widgetRules: FormRules<typeof widgetForm.value> = {
  title: [{ required: true, message: '请输入组件标题', trigger: 'blur' }],
}

function openWidgets(row: Dashboard): void {
  widgetOwner.value = row
  widgetDrawerVisible.value = true
  void widgets.reload()
}

function openWidgetCreate(): void {
  widgetForm.value = { widget_type: 'STAT', title: '', metric_key: '', width: 6, height: 4 }
  widgetDialogVisible.value = true
}

async function submitWidget(): Promise<void> {
  const owner = widgetOwner.value
  const instance = widgetFormRef.value
  if (owner === null || instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    await createWidget(owner.id, {
      widget_type: widgetForm.value.widget_type,
      title: widgetForm.value.title.trim(),
      metric_key: widgetForm.value.metric_key.trim() === '' ? null : widgetForm.value.metric_key.trim(),
      width: widgetForm.value.width,
      height: widgetForm.value.height,
    })
    ElMessage.success('组件已添加')
    widgetDialogVisible.value = false
    await widgets.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function removeWidget(widgetId: string): Promise<void> {
  const owner = widgetOwner.value
  if (owner === null) {
    return
  }
  const confirmed = await confirmAction({
    title: '删除组件',
    message: '确定删除该组件？',
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteWidget(owner.id, widgetId)
    ElMessage.success('组件已删除')
    await widgets.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="仪表盘配置" description="运维看板及其组件">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建仪表盘</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="keyword"
          placeholder="编码 / 名称"
          clearable
          class="dashboards__keyword"
          @keyup.enter="list.search()"
        />
      </div>
      <div class="vctn-toolbar__actions">
        <ElButton @click="list.search()">查询</ElButton>
      </div>
    </div>

    <BaseTable
      :rows="list.rows.value"
      :loading="list.loading.value"
      :failed="list.failed.value"
      :error="list.error.value"
      :total="list.total.value"
      :page="list.page.value"
      :page-size="list.pageSize.value"
      empty-text="没有仪表盘"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="dashboard_code" label="编码" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="name" label="名称" min-width="180" show-overflow-tooltip />
      <ElTableColumn prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <ElTableColumn label="默认" width="90">
        <template #default="{ row }">
          <StatusTag :value="row.is_default" :boolean-labels="['否', '默认']" />
        </template>
      </ElTableColumn>
      <ElTableColumn label="创建人" width="130">
        <template #default="{ row }">{{ orEmpty(row.created_by_username) }}</template>
      </ElTableColumn>
      <ElTableColumn label="更新时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="openWidgets(row)">组件</ElButton>
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建仪表盘' : '编辑仪表盘'" width="520">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="110px">
        <ElFormItem label="编码" prop="dashboard_code">
          <ElInput v-model="form.dashboard_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="名称" prop="name">
          <ElInput v-model="form.name" />
        </ElFormItem>
        <ElFormItem label="说明">
          <ElInput v-model="form.description" type="textarea" :rows="2" />
        </ElFormItem>
        <ElFormItem label="设为默认">
          <ElSwitch v-model="form.is_default" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submit">保存</ElButton>
      </template>
    </ElDialog>

    <ElDrawer v-model="widgetDrawerVisible" :title="`组件 · ${widgetOwner?.name ?? ''}`" size="60%">
      <div class="dashboards__widget-toolbar">
        <ElButton v-if="canManage" size="small" type="primary" @click="openWidgetCreate">
          添加组件
        </ElButton>
      </div>

      <p v-if="widgets.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="widgets.failed.value" class="vctn-muted">
        {{ widgets.error.value ?? '加载失败' }}
      </p>
      <ElTable v-else :data="widgetRows" size="small">
        <ElTableColumn prop="title" label="标题" min-width="160" />
        <ElTableColumn prop="widget_type" label="类型" width="110" />
        <ElTableColumn label="指标键" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ orEmpty(row.metric_key) }}</template>
        </ElTableColumn>
        <ElTableColumn label="尺寸" width="110">
          <template #default="{ row }">{{ row.width }} × {{ row.height }}</template>
        </ElTableColumn>
        <ElTableColumn v-if="canManage" label="操作" width="90">
          <template #default="{ row }">
            <ElButton link type="danger" @click="removeWidget(row.id)">删除</ElButton>
          </template>
        </ElTableColumn>
        <template #empty><span class="vctn-muted">该仪表盘还没有组件</span></template>
      </ElTable>
    </ElDrawer>

    <ElDialog v-model="widgetDialogVisible" title="添加组件" width="480">
      <ElForm ref="widgetFormRef" :model="widgetForm" :rules="widgetRules" label-width="110px">
        <ElFormItem label="类型">
          <ElSelect v-model="widgetForm.widget_type">
            <ElOption v-for="type in WIDGET_TYPE" :key="type" :value="type" :label="type" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="标题" prop="title">
          <ElInput v-model="widgetForm.title" />
        </ElFormItem>
        <ElFormItem label="指标键">
          <ElInput v-model="widgetForm.metric_key" placeholder="选填" />
        </ElFormItem>
        <ElFormItem label="宽度">
          <ElInputNumber v-model="widgetForm.width" :min="1" :max="24" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="高度">
          <ElInputNumber v-model="widgetForm.height" :min="1" :max="24" controls-position="right" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="widgetDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitWidget">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.dashboards__keyword {
  width: 220px;
}

.dashboards__widget-toolbar {
  margin-bottom: var(--vctn-space-3);
}
</style>
