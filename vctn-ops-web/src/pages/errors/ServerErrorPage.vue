<script setup lang="ts">
/** Shown when the backend could not serve a request at all. */
import { ElButton, ElResult } from 'element-plus'

function reload(): void {
  window.location.reload()
}
</script>

<template>
  <div class="gate">
    <ElResult icon="error" title="服务异常" sub-title="后端暂时无法响应，请稍后重试">
      <template #extra>
        <ElButton type="primary" @click="reload">重新加载</ElButton>
      </template>
    </ElResult>
  </div>
</template>

<style scoped>
.gate {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}
</style>
