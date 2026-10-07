<script setup lang="ts">
/** Catch-all page. */
import { ElButton, ElResult } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome(): void {
  void router.replace({ path: '/' })
}
</script>

<template>
  <div class="gate">
    <ElResult icon="info" title="页面不存在" sub-title="该地址没有对应的运维页面">
      <template #extra>
        <ElButton type="primary" @click="goHome">回到控制台</ElButton>
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
