<script setup lang="ts">
/** 404 — no route matched. */
import { useRouter } from 'vue-router'
import { ElButton, ElResult } from 'element-plus'

const router = useRouter()

function goHome(): void {
  void router.replace('/')
}
</script>

<template>
  <ElResult icon="info" title="404" sub-title="页面不存在或已被移除。">
    <template #extra>
      <ElButton type="primary" @click="goHome">回到首页</ElButton>
    </template>
  </ElResult>
</template>
