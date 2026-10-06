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
  padding: var(--vctn-space-4);
  border: 1px solid var(--vctn-border);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  color: var(--vctn-text);
  text-decoration: none;
  transition:
    border-color var(--vctn-duration-base) var(--vctn-ease),
    box-shadow var(--vctn-duration-base) var(--vctn-ease),
    transform var(--vctn-duration-base) var(--vctn-ease);
}

.tool-card:hover {
  border-color: var(--vctn-border-brand);
  box-shadow: var(--vctn-shadow-md);
  transform: translateY(-2px);
}

.tool-card__head {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-2);
}

.tool-card__name {
  margin-right: auto;
  color: var(--vctn-text-strong);
  font-weight: 500;
  font-size: var(--vctn-text-base);
}

.tool-card__summary {
  display: -webkit-box;
  margin: var(--vctn-space-2) 0 0;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
  line-height: 1.6;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tool-card__meta {
  margin-top: var(--vctn-space-3);
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}
</style>
