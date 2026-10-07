<script setup lang="ts">
/** Shown when the identity is valid but the action or the page is refused. */
import { ElButton, ElResult } from 'element-plus'
import { useRouter } from 'vue-router'

import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permission = usePermissionStore()

function goHome(): void {
  void router.replace({ path: permission.landingPath })
}
</script>

<template>
  <div class="gate">
    <ElResult icon="warning" title="无权访问" sub-title="当前账号没有访问该页面的权限">
      <template #extra>
        <ElButton type="primary" @click="goHome">返回可访问页面</ElButton>
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
