<script setup lang="ts">
/** 403 — the identity is valid but the action is refused. */
import { useRouter } from 'vue-router'
import { ElButton, ElResult } from 'element-plus'

const router = useRouter()
</script>

<template>
  <ElResult icon="warning" title="403" sub-title="当前账号没有访问该页面或资源的权限。">
    <template #extra>
      <ElButton type="primary" @click="router.back()">返回上一页</ElButton>
    </template>
  </ElResult>
</template>
