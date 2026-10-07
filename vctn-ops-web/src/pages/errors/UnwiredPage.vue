<script setup lang="ts">
/**
 * Fallback for a menu entry the backend granted but this build does not
 * implement. Rendering it is better than dropping the entry: the operator sees
 * that the permission exists and that the screen is missing, instead of
 * wondering why the menu is short.
 */
import { computed } from 'vue'
import { ElResult, ElTag } from 'element-plus'
import { useRoute } from 'vue-router'

const route = useRoute()

const permissionCode = computed(() => {
  const raw = route.meta.permission
  return typeof raw === 'string' ? raw : ''
})
</script>

<template>
  <div class="gate">
    <ElResult icon="warning" title="页面未接入" sub-title="该菜单节点在本版本控制台中尚未实现">
      <template #extra>
        <ElTag v-if="permissionCode" type="info" effect="light">{{ permissionCode }}</ElTag>
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
