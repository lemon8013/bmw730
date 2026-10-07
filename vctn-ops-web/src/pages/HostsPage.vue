<script setup lang="ts">
/**
 * Monitored hosts.
 *
 * Creating, editing and deleting require `OPS_HOST_MANAGE`; without it the
 * buttons disappear, and the backend refuses the call anyway.
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

import { createHost, deleteHost, listHosts, updateHost } from '@/api/ops/hosts'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { HOST_STATUS } from '@/types/enums'
import type { Host } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const router = useRouter()
const permission = usePermissionStore()

const canManage = computed(() => permission.has(OPS_PERMISSION.hostManage))

const filters = ref({ keyword: '', status: '', environment: '' })

const list = usePagedList<Host>((page, pageSize) =>
  listHosts(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    status: filters.value.status === '' ? undefined : filters.value.status,
    environment: filters.value.environment === '' ? undefined : filters.value.environment,
  }),
)

void list.reload()

/** The row being edited; `null` means the dialog creates a new host. */
const editing = ref<Host | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface HostForm {
  hostname: string
  display_name: string
  ip_address: string
  environment: string
  os_type: string
  cpu_cores: number | null
  memory_total_mb: number | null
  disk_total_gb: number | null
}

const form = ref<HostForm>({
  hostname: '',
  display_name: '',
  ip_address: '',
  environment: 'PRODUCTION',
  os_type: '',
  cpu_cores: null,
  memory_total_mb: null,
  disk_total_gb: null,
})

const rules: FormRules<HostForm> = {
  hostname: [{ required: true, message: '请输入主机名', trigger: 'blur' }],
}

function openCreate(): void {
  editing.value = null
  form.value = {
    hostname: '',
    display_name: '',
    ip_address: '',
    environment: 'PRODUCTION',
    os_type: '',
    cpu_cores: null,
    memory_total_mb: null,
    disk_total_gb: null,
  }
  dialogVisible.value = true
}

function openEdit(row: Host): void {
  editing.value = row
  form.value = {
    hostname: row.hostname,
    display_name: row.display_name ?? '',
    ip_address: row.ip_address ?? '',
    environment: row.environment,
    os_type: row.os_type ?? '',
    cpu_cores: row.cpu_cores,
    memory_total_mb: row.memory_total_mb,
    disk_total_gb: row.disk_total_gb,
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
      await createHost({
        hostname: form.value.hostname.trim(),
        display_name: form.value.display_name.trim() === '' ? null : form.value.display_name.trim(),
        ip_address: form.value.ip_address.trim() === '' ? null : form.value.ip_address.trim(),
        environment: form.value.environment,
        os_type: form.value.os_type.trim() === '' ? null : form.value.os_type.trim(),
        cpu_cores: form.value.cpu_cores,
        memory_total_mb: form.value.memory_total_mb,
        disk_total_gb: form.value.disk_total_gb,
      })
      ElMessage.success('主机已创建')
    } else {
      await updateHost(editing.value.id, {
        display_name: form.value.display_name.trim() === '' ? null : form.value.display_name.trim(),
        ip_address: form.value.ip_address.trim() === '' ? null : form.value.ip_address.trim(),
        environment: form.value.environment,
        os_type: form.value.os_type.trim() === '' ? null : form.value.os_type.trim(),
        cpu_cores: form.value.cpu_cores,
        memory_total_mb: form.value.memory_total_mb,
        disk_total_gb: form.value.disk_total_gb,
      })
      ElMessage.success('主机已更新')
    }
    dialogVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

/** Deleting a host removes its monitoring history, so it asks first. */
async function remove(row: Host): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除主机',
    message: `确定删除主机「${row.display_name || row.hostname}」？该操作不可撤销。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteHost(row.id)
    ElMessage.success('主机已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="主机监控" description="被监控主机的清单与状态">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建主机</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="主机名 / 显示名 / IP"
          clearable
          class="hosts__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.status" placeholder="状态" clearable class="hosts__select">
          <ElOption v-for="status in HOST_STATUS" :key="status" :value="status" :label="status" />
        </ElSelect>
        <ElInput
          v-model="filters.environment"
          placeholder="环境"
          clearable
          class="hosts__select"
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
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="hostname" label="主机名" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="显示名" min-width="160">
        <template #default="{ row }">{{ orEmpty(row.display_name) }}</template>
      </ElTableColumn>
      <ElTableColumn label="IP" width="140">
        <template #default="{ row }">{{ orEmpty(row.ip_address) }}</template>
      </ElTableColumn>
      <ElTableColumn prop="environment" label="环境" width="120" />
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }"><StatusTag :value="row.status" /></template>
      </ElTableColumn>
      <ElTableColumn label="最后心跳" width="180">
        <template #default="{ row }">{{ formatDateTime(row.last_seen_at) }}</template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="router.push({ name: 'ops-host-detail', params: { hostId: row.id } })">
          详情
        </ElButton>
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog
      v-model="dialogVisible"
      :title="editing === null ? '新建主机' : '编辑主机'"
      width="520"
    >
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="110px">
        <ElFormItem label="主机名" prop="hostname">
          <ElInput v-model="form.hostname" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="显示名">
          <ElInput v-model="form.display_name" />
        </ElFormItem>
        <ElFormItem label="IP 地址">
          <ElInput v-model="form.ip_address" />
        </ElFormItem>
        <ElFormItem label="环境">
          <ElInput v-model="form.environment" />
        </ElFormItem>
        <ElFormItem label="操作系统">
          <ElInput v-model="form.os_type" />
        </ElFormItem>
        <ElFormItem label="CPU 核数">
          <ElInputNumber v-model="form.cpu_cores" :min="0" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="内存 (MB)">
          <ElInputNumber v-model="form.memory_total_mb" :min="0" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="磁盘 (GB)">
          <ElInputNumber v-model="form.disk_total_gb" :min="0" controls-position="right" />
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
.hosts__keyword {
  width: 220px;
}

.hosts__select {
  width: 140px;
}
</style>
