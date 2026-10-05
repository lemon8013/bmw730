<script setup lang="ts">
/** One catalogue tool as a clickable card. */
import { computed } from 'vue'

import type { ToolCatalogItem } from '@/types/catalog'
import type { ToolExecutionMode } from '@/types/tool'

const props = defineProps<{
  tool: ToolCatalogItem
  /** Optional rank badge (hot list). */
  rank?: number
  /** Optional usage count line (hot list). */
  usageCount?: number
}>()

const MODE_LABEL: Record<ToolExecutionMode, string> = {
  FRONTEND: '本地处理',
  BACKEND: '在线执行',
  ASYNC: '异步任务',
}

const modeLabel = computed(() => MODE_LABEL[props.tool.execution_mode] ?? props.tool.execution_mode)
const modeTagType = computed(() => {
  switch (props.tool.execution_mode) {
    case 'FRONTEND':
      return 'success'
    case 'ASYNC':
      return 'warning'
    default:
      return 'info'
  }
})
</script>

<template>
  <RouterLink :to="{ name: 'tool', params: { slug: tool.slug } }" class="tool-card">
    <div class="tool-card__head">
      <span class="tool-card__name">{{ tool.name }}</span>
      <ElTag v-if="rank !== undefined" size="small" type="danger" effect="plain">
        #{{ rank }}
      </ElTag>
      <ElTag size="small" :type="modeTagType" effect="plain">{{ modeLabel }}</ElTag>
    </div>
    <p class="tool-card__summary">{{ tool.summary ?? '暂无简介' }}</p>
    <div v-if="usageCount !== undefined" class="tool-card__meta">
      近 7 天使用 {{ usageCount }} 次
    </div>
  </RouterLink>
</template>

<style scoped>
.tool-card {
  display: block;
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: #fff;
  text-decoration: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.tool-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: var(--el-box-shadow-light);
}

.tool-card__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-card__name {
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-right: auto;
}

.tool-card__summary {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tool-card__meta {
  margin-top: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
