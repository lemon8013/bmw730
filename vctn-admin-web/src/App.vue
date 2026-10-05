<script setup lang="ts">
/**
 * Root component.
 *
 * Renders the router outlet and one global "the session ended" notice, so the
 * user learns why they were moved back to the login page instead of being
 * silently redirected.
 */
import { watch } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

watch(
  () => authStore.sessionEnded,
  (ended) => {
    if (!ended) {
      return
    }
    ElMessage.warning('登录状态已失效，请重新登录')
    authStore.sessionEnded = false
    void router.replace({ name: 'login' })
  },
)
</script>

<template>
  <RouterView />
</template>
