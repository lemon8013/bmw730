<script setup lang="ts">
/**
 * Fallback for a menu entry this build does not implement.
 *
 * Shown instead of silently dropping the menu item, so a missing page is
 * visible rather than invisible.
 */
import { useRoute } from 'vue-router'
import { ElAlert, ElResult } from 'element-plus'

const route = useRoute()
</script>

<template>
  <div class="unwired">
    <ElResult icon="warning" title="页面未接入" :sub-title="`后端菜单项 ${route.path} 在当前前端构建中没有对应实现。`" />
    <ElAlert
      type="info"
      :closable="false"
      show-icon
      title="处理方式"
      description="该菜单项来自后端权限树；前端路由映射表 src/router/route-table.ts 中尚未登记对应页面。"
    />
  </div>
</template>

<style scoped>
.unwired {
  max-width: 720px;
  margin: 0 auto;
}
</style>
