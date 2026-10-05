<script setup lang="ts">
/** Tool workbench: title, dynamic input area, execute / clear / copy / download. */
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCard, ElMessage, ElTag } from 'element-plus'

import { getToolJob, toolBySlug } from '@/api/tools'
import AppBreadcrumb from '@/components/AppBreadcrumb.vue'
import AsyncSection from '@/components/AsyncSection.vue'
import FieldInput from '@/components/workbench/FieldInput.vue'
import ToolOutput from '@/components/workbench/ToolOutput.vue'
import { readAnonymousId } from '@/composables/anonymous-id'
import { recordRecentSlug } from '@/composables/recent-tools'
import { useAsyncData } from '@/composables/use-async-data'
import type { ToolCatalogItem } from '@/types/catalog'
import type { ToolExecuteResponse, ToolJobItem } from '@/types/execution'
import { toolRegistry } from '@/tools/registry'
import { toolRuntime } from '@/tools/runtime'
import type { WorkbenchInput } from '@/tools/runtime/executors'

const JOB_TERMINAL = new Set(['SUCCESS', 'FAILED', 'CANCELLED'])

function newTraceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '')
  }
  return Math.random().toString(16).slice(2).padEnd(32, '0')
}

const route = useRoute()
const router = useRouter()
const slug = computed(() => String(route.params.slug ?? ''))

const toolState = useAsyncData<ToolCatalogItem>(() => toolBySlug(slug.value))

const definition = computed(() => toolRegistry.get(toolState.data.value?.component_key ?? ''))

/** The tool exists in the catalogue but has no whitelisted frontend component. */
const notRegistered = computed(
  () => toolState.data.value !== null && definition.value === undefined,
)

// ---------------------------------------------------------------------------
// Input values and execution state
// ---------------------------------------------------------------------------

const values = reactive<Record<string, string | number | boolean>>({})
const executing = ref(false)
const failure = ref<string | null>(null)
const result = ref<ToolExecuteResponse | null>(null)
const job = ref<ToolJobItem | null>(null)
let pollTimer: ReturnType<typeof setTimeout> | null = null

function resetValues(): void {
  for (const key of Object.keys(values)) {
    delete values[key]
  }
  for (const field of definition.value?.fields ?? []) {
    if (field.defaultValue !== undefined) {
      values[field.name] = field.defaultValue
    } else if (field.kind === 'switch') {
      values[field.name] = false
    } else if (field.kind === 'number') {
      values[field.name] = 1
    } else {
      values[field.name] = ''
    }
  }
}

function resetForm(): void {
  resetValues()
  result.value = null
  job.value = null
  failure.value = null
}

watch(
  [toolState.data, definition],
  () => {
    resetForm()
  },
  { immediate: true },
)

function stopPolling(): void {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

async function pollJob(jobId: string): Promise<void> {
  stopPolling()
  const poll = async (attempt: number): Promise<void> => {
    try {
      const item = await getToolJob(jobId)
      job.value = item
      if (JOB_TERMINAL.has(item.status) || attempt >= 20) {
        return
      }
    } catch {
      // Transient failures keep polling until the attempt budget runs out.
      if (attempt >= 20) {
        return
      }
    }
    pollTimer = setTimeout(() => void poll(attempt + 1), 2000)
  }
  void poll(0)
}

async function execute(): Promise<void> {
  const tool = toolState.data.value
  const def = definition.value
  if (tool === null || def === undefined) {
    return
  }

  const missing = (def.fields ?? [])
    .filter((field) => field.required && isVisible(field.name))
    .filter((field) => String(values[field.name] ?? '').trim() === '')
    .map((field) => field.label)
  if (missing.length > 0) {
    failure.value = `请填写：${missing.join('、')}`
    return
  }

  executing.value = true
  failure.value = null
  result.value = null
  job.value = null
  stopPolling()

  const input: WorkbenchInput = {
    toolId: tool.id,
    values: { ...values },
    anonymousId: readAnonymousId(),
  }
  if (def.mode === 'FRONTEND') {
    // The browser produces the result locally; the backend only validates it.
    input.computeLocal = (localValues) => String(localValues.input ?? '')
  }

  try {
    const response = await toolRuntime.execute(def.key, input, {
      traceId: newTraceId(),
      requestId: newTraceId(),
    })
    const payload = response.output as ToolExecuteResponse
    if (!payload.success) {
      failure.value =
        payload.error_message !== null && payload.error_message !== ''
          ? `${payload.error_message}（${payload.error_code ?? ''}）`
          : '执行失败'
    } else {
      result.value = payload
      recordRecentSlug(tool.slug)
      if (payload.job_id !== null) {
        void pollJob(payload.job_id)
      }
    }
  } catch (error: unknown) {
    failure.value = error instanceof Error ? error.message : '执行失败，请稍后重试'
  } finally {
    executing.value = false
  }
}

function isVisible(name: string): boolean {
  const field = (definition.value?.fields ?? []).find((item) => item.name === name)
  if (field?.showWhen === undefined) {
    return true
  }
  return field.showWhen.equals.includes(String(values[field.showWhen.field] ?? ''))
}

// ---------------------------------------------------------------------------
// Copy / download
// ---------------------------------------------------------------------------

const outputRef = ref<InstanceType<typeof ToolOutput> | null>(null)

const downloadable = computed(() => {
  const kind = definition.value?.output
  return kind === 'text' || kind === 'values' || kind === 'digest' || kind === 'json'
})

async function copyOutput(): Promise<void> {
  const text = outputRef.value?.plainText ?? ''
  if (text.trim() === '') {
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败：浏览器未授权剪贴板')
  }
}

function downloadOutput(): void {
  const text = outputRef.value?.plainText ?? ''
  if (text.trim() === '') {
    return
  }
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${toolState.data.value?.slug ?? 'output'}.txt`
  anchor.click()
  URL.revokeObjectURL(url)
}

function goHome(): void {
  void router.push({ name: 'home' })
}
</script>

<template>
  <div class="workbench">
    <AppBreadcrumb :entries="[{ label: toolState.data.value?.name ?? '工具' }]" />

    <AsyncSection
      :loading="toolState.loading.value"
      :failed="toolState.failed.value"
      :error="toolState.error.value"
      @retry="toolState.reload"
    >
      <ElCard shadow="never" class="workbench__head">
        <div class="workbench__head-inner">
          <div>
            <h1 class="workbench__title">{{ toolState.data.value?.name }}</h1>
            <p class="workbench__desc">
              {{ toolState.data.value?.summary ?? toolState.data.value?.description ?? '暂无说明' }}
            </p>
          </div>
          <div class="workbench__tags">
            <ElTag size="small" type="info">
              {{ definition?.mode ?? toolState.data.value?.execution_mode }}
            </ElTag>
            <ElButton size="small" @click="goHome">返回首页</ElButton>
          </div>
        </div>
      </ElCard>

      <ElAlert
        v-if="notRegistered"
        type="warning"
        :closable="false"
        show-icon
        class="workbench__notice"
        :title="`组件 ${toolState.data.value?.component_key} 尚未在前端注册`"
        description="目录里有这个工具，但前端还没有对应的白名单组件，暂不能执行。"
      />

      <template v-else-if="definition !== undefined">
        <ElCard shadow="never" class="workbench__section">
          <template #header>输入</template>

          <FieldInput
            v-for="field in definition.fields ?? []"
            :key="field.name"
            v-model="values[field.name]"
            :descriptor="field"
            :all-values="values"
          />

          <div class="workbench__actions">
            <ElButton type="primary" :loading="executing" @click="execute">执行</ElButton>
            <ElButton :disabled="executing" @click="resetForm">清空</ElButton>
            <span v-if="definition.mode === 'FRONTEND'" class="workbench__privacy">
              该工具在浏览器本地处理，输入内容不会上传。
            </span>
          </div>
        </ElCard>

        <ElCard v-if="failure !== null" shadow="never" class="workbench__section">
          <ElAlert type="error" :closable="false" show-icon :title="failure" />
        </ElCard>

        <ElCard v-if="result !== null" shadow="never" class="workbench__section">
          <template #header>
            <div class="workbench__output-head">
              <span>结果</span>
              <span class="workbench__duration">耗时 {{ result.duration_ms }} ms</span>
              <ElButton size="small" @click="copyOutput">复制</ElButton>
              <ElButton v-if="downloadable" size="small" @click="downloadOutput">下载</ElButton>
            </div>
          </template>

          <ToolOutput ref="outputRef" :kind="definition.output ?? 'text'" :output="result.output" />
        </ElCard>

        <ElCard v-if="job !== null" shadow="never" class="workbench__section">
          <template #header>异步任务</template>
          <ElAlert
            :type="job.status === 'SUCCESS' ? 'success' : job.status === 'FAILED' ? 'error' : 'info'"
            :closable="false"
            show-icon
            :title="`任务 ${job.id} · ${job.status}`"
            :description="job.last_error ?? '已在队列中，可用任务 ID 继续查询状态。'"
          />
        </ElCard>

        <p class="workbench__quota">
          当前以匿名身份执行（{{ toolState.data.value?.execution_mode }}），受匿名额度与频率限制约束。
        </p>
      </template>
    </AsyncSection>
  </div>
</template>

<style scoped>
.workbench__head {
  margin-bottom: 16px;
}

.workbench__head-inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.workbench__title {
  margin: 0 0 6px;
  font-size: 20px;
}

.workbench__desc {
  margin: 0;
  color: var(--el-text-color-secondary);
}

.workbench__notice {
  margin-bottom: 16px;
}

.workbench__section {
  margin-bottom: 16px;
}

.workbench__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workbench__privacy {
  color: var(--el-color-success);
  font-size: 12px;
}

.workbench__output-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.workbench__duration {
  margin-right: auto;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.workbench__quota {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
