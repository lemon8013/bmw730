<script setup lang="ts">
/**
 * The four states of an asynchronous region, in one place.
 *
 * Pages that are not tables (dashboards, detail panes) use this so they can
 * never end up as a blank screen: loading, failure with retry, empty and ready
 * are all rendered explicitly.
 */
import { ElAlert, ElButton, ElEmpty, ElSkeleton, ElSkeletonItem } from 'element-plus'

import type { RenderedError } from '@/utils/error'

interface Props {
  loading: boolean
  failed: boolean
  empty: boolean
  error?: RenderedError | null
  emptyText?: string
  /** How many skeleton rows to draw while loading. */
  skeletonRows?: number
}

withDefaults(defineProps<Props>(), {
  error: null,
  emptyText: '暂无数据',
  skeletonRows: 4,
})

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="data-state">
    <template v-if="loading">
      <ElSkeleton :rows="0" animated>
        <template #template>
          <ElSkeletonItem
            v-for="row in skeletonRows"
            :key="row"
            variant="text"
            class="data-state__skeleton"
          />
        </template>
      </ElSkeleton>
    </template>

    <template v-else-if="failed">
      <ElAlert
        type="error"
        :closable="false"
        show-icon
        title="加载失败"
        :description="error?.message ?? '请稍后重试'"
      />
      <div class="data-state__actions">
        <ElButton type="primary" @click="emit('retry')">重试</ElButton>
        <span v-if="error?.traceId" class="data-state__trace">
          Trace ID: {{ error.traceId }}
        </span>
      </div>
    </template>

    <ElEmpty v-else-if="empty" :description="emptyText" />

    <slot v-else />
  </div>
</template>

<style scoped>
.data-state__skeleton {
  margin-bottom: 12px;
}

.data-state__actions {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
}

.data-state__trace {
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
