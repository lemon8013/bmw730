<script setup lang="ts">
/**
 * One monitored host.
 *
 * The detail pane is read-mostly: it shows everything the list cannot afford to
 * (tags, specifications, the bound agent) and offers the same edit form as the
 * list when the caller may write.
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
  ElInputNumber,
  ElMessage,
  ElOption,
  ElSelect,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { getHost, updateHost } from '@/api/ops/hosts'
import DataStateView from '@/components/common/DataStateView.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { useAsyncData } from '@/composables/use-async-data'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import { HOST_STATUS } from '@/types/enums'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const permission = usePermissionStore()

const canManage = computed(() => permission.has(OPS_PERMISSION.hostManage))

const hostId = computed(() => {
  const raw = route.params.hostId
  return typeof raw === 'string' ? raw : ''
})

const host = useAsyncData(() => getHost(hostId.value))

const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface HostForm {
  display_name: string
  ip_address: string
  environment: string
  status: string
  cpu_cores: number | null
  memory_total_mb: number | null
  disk_total_gb: number | null
}

const form = ref<HostForm>({
  display_name: '',
  ip_address: '',
  environment: 'PRODUCTION',
  status: 'ONLINE',
  cpu_cores: null,
  memory_total_mb: null,
  disk_total_gb: null,
})

const rules: FormRules<HostForm> = {
  environment: [{ required: true, message: '请输入环境', trigger: 'blur' }],
}

function openEdit(): void {
  const current = host.data.value
  if (current === null) {
    return
  }
  form.value = {
    display_name: current.display_name ?? '',
    ip_address: current.ip_address ?? '',
    environment: current.environment,
    status: current.status,
    cpu_cores: current.cpu_cores,
    memory_total_mb: current.memory_total_mb,
    disk_total_gb: current.disk_total_gb,
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
    await updateHost(hostId.value, {
      display_name: form.value.display_name.trim() === '' ? null : form.value.display_name.trim(),
      ip_address: form.value.ip_address.trim() === '' ? null : form.value.ip_address.trim(),
      environment: form.value.environment,
      status: form.value.status,
      cpu_cores: form.value.cpu_cores,
      memory_total_mb: form.value.memory_total_mb,
      disk_total_gb: form.value.disk_total_gb,
    })
    ElMessage.success('主机已更新')
    dialogVisible.value = false
    await host.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader
      :title="host.data.value?.display_name || host.data.value?.hostname || '主机详情'"
      description="主机登记信息与运行状态"
    >
      <template #actions>
        <ElButton @click="router.push({ name: 'ops-hosts' })">返回列表</ElButton>
        <ElButton v-if="canManage" type="primary" @click="openEdit">编辑</ElButton>
      </template>
    </PageHeader>

    <DataStateView
      :loading="host.loading.value"
      :failed="host.failed.value"
      :empty="host.data.value === null"
      :error="host.error.value"
      empty-text="主机不存在或无权查看"
      @retry="host.reload()"
    >
      <div class="vctn-panel">
        <ElDescriptions :column="2" border>
          <ElDescriptionsItem label="主机名">{{ host.data.value?.hostname }}</ElDescriptionsItem>
          <ElDescriptionsItem label="显示名">
            {{ orEmpty(host.data.value?.display_name) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="IP 地址">
            {{ orEmpty(host.data.value?.ip_address) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="环境">{{ host.data.value?.environment }}</ElDescriptionsItem>
          <ElDescriptionsItem label="状态">
            <StatusTag :value="host.data.value?.status ?? ''" />
          </ElDescriptionsItem>
          <ElDescriptionsItem label="操作系统">
            {{ orEmpty(host.data.value?.os_type) }} {{ orEmpty(host.data.value?.os_version) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="CPU 核数">
            {{ orEmpty(host.data.value?.cpu_cores) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="内存 (MB)">
            {{ orEmpty(host.data.value?.memory_total_mb) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="磁盘 (GB)">
            {{ orEmpty(host.data.value?.disk_total_gb) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="绑定 Agent">
            {{ orEmpty(host.data.value?.agent_id) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="最后心跳">
            {{ formatDateTime(host.data.value?.last_seen_at) }}
          </ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">
            {{ formatDateTime(host.data.value?.created_at) }}
          </ElDescriptionsItem>
        </ElDescriptions>
      </div>

      <div v-if="host.data.value?.tags" class="vctn-panel">
        <h3 class="vctn-section-title">标签</h3>
        <pre class="host-detail__tags">{{ JSON.stringify(host.data.value.tags, null, 2) }}</pre>
      </div>
    </DataStateView>

    <ElDialog v-model="dialogVisible" title="编辑主机" width="520">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="110px">
        <ElFormItem label="显示名">
          <ElInput v-model="form.display_name" />
        </ElFormItem>
        <ElFormItem label="IP 地址">
          <ElInput v-model="form.ip_address" />
        </ElFormItem>
        <ElFormItem label="环境" prop="environment">
          <ElInput v-model="form.environment" />
        </ElFormItem>
        <ElFormItem label="状态">
          <ElSelect v-model="form.status">
            <ElOption v-for="status in HOST_STATUS" :key="status" :value="status" :label="status" />
          </ElSelect>
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
.host-detail__tags {
  margin: 0;
  padding: var(--vctn-space-3);
  border-radius: var(--vctn-radius-md);
  background-color: var(--vctn-bg-inset);
  color: var(--vctn-text-regular);
  font-family: var(--vctn-font-mono);
  font-size: var(--vctn-text-xs);
  overflow-x: auto;
}
</style>
