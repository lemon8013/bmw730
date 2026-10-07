<script setup lang="ts">
/**
 * Availability probes.
 *
 * The probe definitions are writable; their results are history and are only
 * read, through a drawer, because a result row is only meaningful next to the
 * check that produced it.
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
  createAvailabilityCheck,
  deleteAvailabilityCheck,
  listAvailabilityChecks,
  listAvailabilityResults,
  updateAvailabilityCheck,
} from '@/api/ops/availability'
import PageHeader from '@/components/common/PageHeader.vue'
import BaseTable from '@/components/table/BaseTable.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { usePagedList } from '@/composables/use-paged-list'
import { useAsyncData } from '@/composables/use-async-data'
import { confirmAction } from '@/composables/useConfirm'
import { usePermissionStore } from '@/stores/permission'
import { OPS_PERMISSION } from '@/constants/permissions'
import type { AvailabilityCheck } from '@/types/ops'
import { formatDateTime, orEmpty } from '@/utils/format'
import { renderError } from '@/utils/error'

const permission = usePermissionStore()
const canManage = computed(() => permission.has(OPS_PERMISSION.monitorManage))

const CHECK_TYPES = ['HTTP', 'HTTPS', 'TCP', 'ICMP', 'DNS'] as const

const filters = ref({
  keyword: '',
  checkType: '',
  environment: '',
  enabled: undefined as boolean | undefined,
})

const list = usePagedList<AvailabilityCheck>((page, pageSize) =>
  listAvailabilityChecks(page, pageSize, {
    keyword: filters.value.keyword.trim() === '' ? undefined : filters.value.keyword.trim(),
    checkType: filters.value.checkType === '' ? undefined : filters.value.checkType,
    environment: filters.value.environment === '' ? undefined : filters.value.environment,
    enabled: filters.value.enabled,
  }),
)

void list.reload()

/* ---------- edit ---------- */

const editing = ref<AvailabilityCheck | null>(null)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface CheckForm {
  check_code: string
  name: string
  check_type: string
  target: string
  environment: string
  timeout_ms: number
  interval_seconds: number
  expected_status: number | null
  enabled: boolean
}

const form = ref<CheckForm>({
  check_code: '',
  name: '',
  check_type: 'HTTP',
  target: '',
  environment: 'PRODUCTION',
  timeout_ms: 5000,
  interval_seconds: 60,
  expected_status: 200,
  enabled: true,
})

const rules: FormRules<CheckForm> = {
  check_code: [{ required: true, message: '请输入探测编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  target: [{ required: true, message: '请输入探测目标', trigger: 'blur' }],
}

function openCreate(): void {
  editing.value = null
  form.value = {
    check_code: '',
    name: '',
    check_type: 'HTTP',
    target: '',
    environment: 'PRODUCTION',
    timeout_ms: 5000,
    interval_seconds: 60,
    expected_status: 200,
    enabled: true,
  }
  dialogVisible.value = true
}

function openEdit(row: AvailabilityCheck): void {
  editing.value = row
  form.value = {
    check_code: row.check_code,
    name: row.name,
    check_type: row.check_type,
    target: row.target,
    environment: row.environment,
    timeout_ms: row.timeout_ms,
    interval_seconds: row.interval_seconds,
    expected_status: row.expected_status,
    enabled: row.enabled,
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
      await createAvailabilityCheck({
        check_code: form.value.check_code.trim(),
        name: form.value.name.trim(),
        check_type: form.value.check_type,
        target: form.value.target.trim(),
        environment: form.value.environment,
        timeout_ms: form.value.timeout_ms,
        interval_seconds: form.value.interval_seconds,
        expected_status: form.value.expected_status,
        enabled: form.value.enabled,
      })
      ElMessage.success('探测已创建')
    } else {
      await updateAvailabilityCheck(editing.value.id, {
        name: form.value.name.trim(),
        target: form.value.target.trim(),
        environment: form.value.environment,
        timeout_ms: form.value.timeout_ms,
        interval_seconds: form.value.interval_seconds,
        expected_status: form.value.expected_status,
        enabled: form.value.enabled,
      })
      ElMessage.success('探测已更新')
    }
    dialogVisible.value = false
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}

/** Element Plus hands rows back as a loose record; narrow it for the handler. */
function asAvailabilityCheck(row: unknown): AvailabilityCheck {
  return row as AvailabilityCheck
}

async function toggle(row: AvailabilityCheck, enabled: boolean): Promise<void> {
  try {
    await updateAvailabilityCheck(row.id, { enabled })
    ElMessage.success(enabled ? '探测已启用' : '探测已停用')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

async function remove(row: AvailabilityCheck): Promise<void> {
  const confirmed = await confirmAction({
    title: '删除探测',
    message: `确定删除探测「${row.name}」？该操作不可撤销。`,
    confirmText: '删除',
  })
  if (!confirmed) {
    return
  }
  try {
    await deleteAvailabilityCheck(row.id)
    ElMessage.success('探测已删除')
    await list.reload()
  } catch (caught: unknown) {
    ElMessage.error(renderError(caught).message)
  }
}

/* ---------- results ---------- */

const resultsCheck = ref<AvailabilityCheck | null>(null)
const resultsVisible = ref(false)
const resultsHours = ref(24)

const results = useAsyncData(() =>
  resultsCheck.value === null
    ? Promise.resolve(null)
    : listAvailabilityResults(resultsCheck.value.id, 1, 50, resultsHours.value),
)

const resultRows = computed(() => results.data.value?.items ?? [])

function openResults(row: AvailabilityCheck): void {
  resultsCheck.value = row
  resultsVisible.value = true
  void results.reload()
}
</script>

<template>
  <div class="vctn-page">
    <PageHeader title="可用性" description="主动探测定义与其执行结果">
      <template #actions>
        <ElButton v-if="canManage" type="primary" @click="openCreate">新建探测</ElButton>
      </template>
    </PageHeader>

    <div class="vctn-toolbar">
      <div class="vctn-toolbar__filters">
        <ElInput
          v-model="filters.keyword"
          placeholder="编码 / 名称"
          clearable
          class="availability__keyword"
          @keyup.enter="list.search()"
        />
        <ElSelect v-model="filters.checkType" placeholder="类型" clearable class="availability__field">
          <ElOption v-for="type in CHECK_TYPES" :key="type" :value="type" :label="type" />
        </ElSelect>
        <ElInput v-model="filters.environment" placeholder="环境" clearable class="availability__field" />
        <span class="vctn-muted">仅看启用</span>
        <ElSwitch v-model="filters.enabled" />
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
      empty-text="没有可用性探测"
      @retry="list.reload()"
      @update:page="list.changePage"
      @update:page-size="list.changePageSize"
    >
      <ElTableColumn prop="check_code" label="编码" min-width="150" show-overflow-tooltip />
      <ElTableColumn prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <ElTableColumn prop="check_type" label="类型" width="100" />
      <ElTableColumn prop="target" label="目标" min-width="200" show-overflow-tooltip />
      <ElTableColumn prop="environment" label="环境" width="110" />
      <ElTableColumn label="间隔 (秒)" width="110">
        <template #default="{ row }">{{ row.interval_seconds }}</template>
      </ElTableColumn>
      <ElTableColumn label="超时 (ms)" width="110">
        <template #default="{ row }">{{ row.timeout_ms }}</template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElSwitch
            :model-value="row.enabled"
            :disabled="!canManage"
            @update:model-value="toggle(asAvailabilityCheck(row), $event === true)"
          />
        </template>
      </ElTableColumn>

      <template #operations="{ row }">
        <ElButton link type="primary" @click="openResults(row)">结果</ElButton>
        <ElButton v-if="canManage" link type="primary" @click="openEdit(row)">编辑</ElButton>
        <ElButton v-if="canManage" link type="danger" @click="remove(row)">删除</ElButton>
      </template>
    </BaseTable>

    <ElDialog v-model="dialogVisible" :title="editing === null ? '新建探测' : '编辑探测'" width="540">
      <ElForm ref="formRef" :model="form" :rules="rules" label-width="130px">
        <ElFormItem label="探测编码" prop="check_code">
          <ElInput v-model="form.check_code" :disabled="editing !== null" />
        </ElFormItem>
        <ElFormItem label="名称" prop="name">
          <ElInput v-model="form.name" />
        </ElFormItem>
        <ElFormItem label="类型">
          <ElSelect v-model="form.check_type">
            <ElOption v-for="type in CHECK_TYPES" :key="type" :value="type" :label="type" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="目标" prop="target">
          <ElInput v-model="form.target" placeholder="https://example.com/health" />
        </ElFormItem>
        <ElFormItem label="环境">
          <ElInput v-model="form.environment" />
        </ElFormItem>
        <ElFormItem label="超时 (ms)">
          <ElInputNumber v-model="form.timeout_ms" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="间隔 (秒)">
          <ElInputNumber v-model="form.interval_seconds" :min="1" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="期望状态码">
          <ElInputNumber v-model="form.expected_status" controls-position="right" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitting" @click="submit">保存</ElButton>
      </template>
    </ElDialog>

    <ElDrawer v-model="resultsVisible" :title="`探测结果 · ${resultsCheck?.name ?? ''}`" size="60%">
      <div class="availability__results-toolbar">
        <ElSelect v-model="resultsHours" class="availability__field" @change="results.reload()">
          <ElOption :value="1" label="近 1 小时" />
          <ElOption :value="24" label="近 24 小时" />
          <ElOption :value="72" label="近 3 天" />
          <ElOption :value="168" label="近 7 天" />
        </ElSelect>
      </div>

      <p v-if="results.loading.value" class="vctn-muted">加载中…</p>
      <p v-else-if="results.failed.value" class="vctn-muted">
        {{ results.error.value ?? '加载失败' }}
      </p>
      <ElTable v-else :data="resultRows" size="small">
        <ElTableColumn label="探测时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.checked_at) }}</template>
        </ElTableColumn>
        <ElTableColumn label="结果" width="100">
          <template #default="{ row }">
            <StatusTag :value="row.success" :boolean-labels="['失败', '成功']" />
          </template>
        </ElTableColumn>
        <ElTableColumn label="延迟 (ms)" width="120">
          <template #default="{ row }">{{ orEmpty(row.latency_ms) }}</template>
        </ElTableColumn>
        <ElTableColumn label="状态码" width="100">
          <template #default="{ row }">{{ orEmpty(row.status_code) }}</template>
        </ElTableColumn>
        <ElTableColumn prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
        <template #empty><span class="vctn-muted">窗口内没有探测结果</span></template>
      </ElTable>
    </ElDrawer>
  </div>
</template>

<style scoped>
.availability__keyword {
  width: 200px;
}

.availability__field {
  width: 140px;
}

.availability__results-toolbar {
  margin-bottom: var(--vctn-space-3);
}
</style>
