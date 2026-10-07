<script setup lang="ts">
/**
 * One monitored service, with the dependency edges it declares.
 *
 * Dependencies live here rather than on the list because adding an edge needs
 * the service in front of you: the operator picks what this service calls.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElOption,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import {
  addDependency,
  getService,
  listDependencies,
  removeDependency,
  updateService,
} from '@/api/ops/services'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { SERVICE_STATUS } from '@/types/enums'
import type { Service } from '@/types/ops'
import { formatDateTime, formatPercent, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const permission = usePermissionStore()

const canManage = computed(() => permission.has(OPS_PERMISSION.serviceManage))

const serviceId = computed(() => {
  const raw = route.params.serviceId
  return typeof raw === 'string' ? raw : ''
})

const service = useAsyncData<Service | null>(() => getService(serviceId.value))
const dependencies = useAsyncData(() => listDependencies(serviceId.value, 1, 50))

const dependencyRows = computed(() => dependencies.data.value?.items ?? [])

const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = ref({ status: 'UP' })
const rules: FormRules<typeof form.value> = {
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const dependencyDialogVisible = ref(false)
const dependencyForm = ref({ depends_on_service_id: '', dependency_type: 'CALLS' })
const dependencyFormRef = ref<FormInstance>()
const dependencyRules: FormRules<typeof dependencyForm.value> = {
  depends_on_service_id: [{ required: true, message: '请输入被依赖服务 ID', trigger: 'blur' }],
}

function openEdit(): void {
  form.value.status = service.data.value?.status ?? 'UP'
  dialogVisible.value = true
}

async function submitStatus(): Promise<void> {
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
    await updateService(serviceId.value, { status: form.value.status })
    ElMessage.success('服务状态已更新')
    dialogVisible.value = false
    await service.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function submitDependency(): Promise<void> {
  const instance = dependencyFormRef.value
  if (instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    await addDependency(serviceId.value, {
      depends_on_service_id: dependencyForm.value.depends_on_service_id.trim(),
      dependency_type: dependencyForm.value.dependency_type,
    })
    ElMessage.success('依赖已添加')
    dependencyDialogVisible.value = false
    await dependencies.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function removeDependencyEdge(dependencyId: string): Promise<void> {
  const confirmed = await confirmAction({
    title: '移除依赖',
    message: '确定移除这条依赖边？',
    confirmText: '移除',
  })
  if (!confirmed) {
    return
  }
  try {
    await removeDependency(serviceId.value, dependencyId)
    ElMessage.success('依赖已移除')
    await dependencies.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader
      :title="service.data.value?.service_name || '服务详情'"
      :description="service.data.value?.service_code"
    >
      <template #actions>
        <ElButton @click="router.push({ name: 'ops-services' })">返回列表</ElButton>
        <ElButton v-if="canManage" type="primary" @click="openEdit">修改状态</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="service.loading.value"
      :failed="service.failed.value"
      :empty="service.data.value === null"
      :error="service.error.value"
      empty-text="服务不存在或无权查看"
      @retry="service.reload()"
    >
      <div class="vctn-panel">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="服务编码">
            {{ service.data.value?.service_code }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="服务名称">
            {{ service.data.value?.service_name }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="类型">{{ service.data.value?.service_type }}</ElDescriptionsItem>
          <ElDescriptionsItem label="环境">{{ service.data.value?.environment }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <StatusTag :value="service.data.value?.status ?? ''" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="主机">
            {{ orEmpty(service.data.value?.host_id) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="可用性">
            {{ formatPercent(service.data.value?.availability_rate) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="错误率">
            {{ formatPercent(service.data.value?.error_rate) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="平均延迟 (ms)">
            {{ orEmpty(service.data.value?.avg_latency_ms) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="最后检查">
            {{ formatDateTime(service.data.value?.last_check_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </div>
    </DataStateView>

    <div class="vctn-panel vctn-panel--flush">
      <div class="service-detail__deps-header">
        <h3 class="vctn-section-title">依赖</h3>
        <ElButton v-if="canManage" size="small" type="primary" @click="dependencyDialogVisible = true">
          添加依赖
        </ElButton>
      </div>

      <DataStateView
        :loading="dependencies.loading.value"
        :failed="dependencies.failed.value"
        :empty="dependencyRows.length === 0"
        :error="dependencies.error.value"
        empty-text="该服务尚未声明依赖"
        :skeleton-rows="2"
        @retry="dependencies.reload()"
      >
        <ElTable :data="dependencyRows">
          <ElTableColumn prop="depends_on_service_id" label="被依赖服务" min-width="200" />
          <ElTableColumn label="依赖类型" width="140">
            <template #default="{ row }">
              <ElTag size="small" effect="light">{{ row.dependency_type }}</ElTag>
            </template>
          </ElTableColumn>
          <ElTableColumn label="创建时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </ElTableColumn>
          <ElTableColumn v-if="canManage" label="操作" width="100">
            <template #default="{ row }">
              <ElButton link type="danger" @click="removeDependencyEdge(row.id)">移除</ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
      </DataStateView>
    </div>

    <ElDialog v-model="dialogVisible" title="修改服务状态" width="420">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="90px">
        <ElFormItem label="状态" prop="status">
          <ElSelect v-model="form.status">
            <ElOption v-for="status in SERVICE_STATUS" :key="status" :value="status" :label="status" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitStatus">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="dependencyDialogVisible" title="添加依赖" width="460">
      <ElForm ref="dependencyFormRef" :model="dependencyForm" :rules="dependencyRules" label-width="120px">
        <ElFormItem label="被依赖服务 ID" prop="depends_on_service_id">
          <ElInput v-model="dependencyForm.depends_on_service_id" />
        </ElFormItem>
        <ElFormItem label="依赖类型">
          <ElInput v-model="dependencyForm.dependency_type" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dependencyDialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submitDependency">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.service-detail__deps-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--vctn-space-4) var(--vctn-space-4) 0;
}
</style>
