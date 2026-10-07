<script setup lang="ts">
/**
 * Monitored services.
 *
 * Creating, editing and deleting require `OPS_SERVICE_MANAGE`; a dependency
 * edge is managed from the service detail page, where both ends are visible.
 */
import { computed, ref } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  ElTableColumn,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { useRouter } from 'vue-router'

import { createService, deleteService, listServices, updateService } from '@/api/ops/services'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { SERVICE_STATUS } from '@/types/enums'
import type { Service } from '@/types/ops'
import { formatDateTime, formatPercent, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const router = useRouter()
const permission = usePermissionStore()

const canManage = computed(() => permission.has(OPS_PERMISSION.serviceManage))

const filters = ref({ keyword: '', status: '', environment: '' })

const list = usePagedList<Service>((page, pageSize) =>
  listServices(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    status: filters.value.status === '' ? undefined : filters.value.status,
    environment: filters.value.environment === '' ? undefined : filters.value.environment,
  }),
)

void list.reload()

const editing = ref<Service | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface ServiceForm {
  service_code: string
  service_name: string
  service_type: string
  environment: string
  host_id: string
  status: string
  availability_rate: number | null
  error_rate: number | null
  avg_latency_ms: number | null
}

const form = ref<ServiceForm>({
  service_code: '',
  service_name: '',
  service_type: 'APPLICATION',
  environment: 'PRODUCTION',
  host_id: '',
  status: 'UP',
  availability_rate: null,
  error_rate: null,
  avg_latency_ms: null,
})

const rules: FormRules<ServiceForm> = {
  service_code: [{ required: true, message: '请输入服务编码', trigger: 'blur' }],
  service_name: [{ required: true, message: '请输入服务名称', trigger: 'blur' }],
}

function openCreate(): void {
  editing.value = null
  form.value = {
    service_code: '',
    service_name: '',
    service_type: 'APPLICATION',
    environment: 'PRODUCTION',
    host_id: '',
    status: 'UP',
    availability_rate: null,
    error_rate: null,
    avg_latency_ms: null,
  }
  dialogVisible.value = true
}

function openEdit(row: Service): void {
  editing.value = row
  form.value = {
    service_code: row.service_code,
    service_name: row.service_name,
    service_type: row.service_type,
    environment: row.environment,
    host_id: row.host_id ?? '',
    status: row.status,
    availability_rate: row.availability_rate,
    error_rate: row.error_rate,
    avg_latency_ms: row.avg_latency_ms,
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
      await createService({
        service_code: form.value.service_code.trim(),
        service_name: form.value.service_name.trim(),
        service_type: form.value.service_type,
        environment: form.value.environment,
        host_id: form.value.host_id.trim() === '' ? null : form.value.host_id.trim(),
      })
      ElMessage.success('服务已创建')
    } else {
      await updateService(editing.value.id, {
        service_name: form.value.service_name.trim(),
        service_type: form.value.service_type,
        environment: form.value.environment,
        host_id: form.value.host_id.trim() === '' ? null : form.value.host_id.trim(),
        status: form.value.status,
        availability_rate: form.value.availability_rate,
        error_rate: form.value.error_rate,
        avg_latency_ms: form.value.avg_latency_ms,
      })
      ElMessage.success('服务已更新')
    }
    dialogVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

async function remove(row: Service): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除服务',
    message: `确定删除服务「${row.service_name}」？该操作不可撤销。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteService(row.id)
    ElMessage.success('服务已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="服务监控" description="被监控服务的健康度与依赖">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建服务</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="服务编码 / 名称"
          clearable
          class="services__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.status" placeholder="状态" clearable class="services__select">
          <ElOption v-for="status in SERVICE_STATUS" :key="status" :value="status" :label="status" />
        </ElSelect>
        <ElInput v-model="filters.environment" placeholder="环境" clearable class="services__select" />
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
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="service_code" label="服务编码" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="service_name" label="服务名称" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="service_type" label="类型" width="120" />
      <ElTableColumn prop="environment" label="环境" width="110" />
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }"><StatusTag :value="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn label="可用性" width="110">
        <template #default="{ row }">{{ formatPercent(row.availability_rate) }}</template>
      </ElTableColumn>
      <ElTableColumn label="错误率" width="110">
        <template #default="{ row }">{{ formatPercent(row.error_rate) }}</template>
      </ElTableColumn>
      <ElTableColumn label="平均延迟 (ms)" width="130">
        <template #default="{ row }">{{ orEmpty(row.avg_latency_ms) }}</template>
      </ElTableColumn>
      <ElTableColumn label="最后检查" width="180">
        <template #default="{ row }">{{ formatDateTime(row.last_check_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton
          link
          type="primary"
          @click="router.push({ name: 'ops-service-detail', params: { serviceId: row.id } })"
        >
          详情
        </ElButton>
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建服务' : '编辑服务'" width="520">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="120px">
        <ElFormItem label="服务编码" prop="service_code">
          <ElInput v-model="form.service_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="服务名称" prop="service_name">
          <ElInput v-model="form.service_name" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElInput v-model="form.service_type" />
        </ElFormItem>
        <ElFormItem label="环境">
          <ElInput v-model="form.environment" />
        </ElFormItem>
        <ElFormItem label="主机 ID">
          <ElInput v-model="form.host_id" placeholder="选填" />
        </ElFormItem>
        <ElFormItem v-if="editing !== null" label="状态">
          <ElSelect v-model="form.status">
            <ElOption v-for="status in SERVICE_STATUS" :key="status" :value="status" :label="status" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="editing !== null" label="可用性">
          <ElInputNumber
            v-model="form.availability_rate"
            :min="0"
            :max="1"
            :step="0.01"
            controls-position="right"
          />
        </ElFormItem>
        <ElFormItem v-if="editing !== null" label="错误率">
          <ElInputNumber
            v-model="form.error_rate"
            :min="0"
            :max="1"
            :step="0.01"
            controls-position="right"
          />
        </ElFormItem>
        <ElFormItem v-if="editing !== null" label="平均延迟 (ms)">
          <ElInputNumber v-model="form.avg_latency_ms" :min="0" controls-position="right" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submit">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.services__keyword {
  width: 220px;
}

.services__select {
  width: 140px;
}
</style>
