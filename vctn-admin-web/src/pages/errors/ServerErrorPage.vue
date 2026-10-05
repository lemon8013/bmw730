<script setup lang="ts">
/** 500 — the backend reported an internal failure. */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElButton, ElResult } from 'element-plus'

const route = useRoute()
const router = useRouter()

/** The trace id is echoed when the failing request carried one. */
const traceId = computed(() => {
  const value = route.query.trace_id
  return typeof value === 'string' && value.length > 0 ? value : null
})

function retry(): void {
  window.location.reload()
}
</script>

<template>
  <ElResult icon="error" title="500" sub-title="服务端出现异常，请稍后重试。">
    <p v-if="traceId" class="error-trace">Trace ID: {{ traceId }}</p>
    <template #extra>
      <ElButton type="primary" @click="retry">重新加载</ElButton>
      <ElButton @click="router.back()">返回上一页</ElButton>
    </template>
  </ElResult>
</template>

<style scoped>
.error-trace {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
