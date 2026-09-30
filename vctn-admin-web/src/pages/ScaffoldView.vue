<script setup lang="ts">
import { ElCard, ElDescriptions, ElDescriptionsItem, ElTag } from 'element-plus'
import { version as vueVersion } from 'vue'
import { useRoute } from 'vue-router'

import { apiBaseUrl } from '@/api/client'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()
</script>

<template>
  <main class="scaffold">
    <ElCard>
      <template #header>
        <strong>{{ appStore.applicationName }}</strong>
        <ElTag class="scaffold__tag" type="info" size="small">{{ appStore.buildPhase }}</ElTag>
      </template>

      <ElDescriptions :column="1" border>
        <ElDescriptionsItem label="Vue">{{ vueVersion }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Vue Router">route {{ route.path }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Pinia">{{ appStore.applicationName }}</ElDescriptionsItem>
        <ElDescriptionsItem label="Element Plus">components registered</ElDescriptionsItem>
        <ElDescriptionsItem label="API base URL">{{ apiBaseUrl }}</ElDescriptionsItem>
      </ElDescriptions>
    </ElCard>
  </main>
</template>

<style scoped>
.scaffold {
  padding: 24px;
}

.scaffold__tag {
  margin-left: 8px;
}
</style>
