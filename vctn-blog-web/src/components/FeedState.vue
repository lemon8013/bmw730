<script setup lang="ts">
/**
 * Loading / empty / failed state for a feed.
 *
 * Kept as one component so every list page reports the same three situations in
 * the same words instead of inventing its own copy.
 */
defineProps<{
  loading: boolean
  failed: boolean
  error: string | null
  empty: boolean
  emptyText?: string
}>()

defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="feed-state">
    <ElSkeleton v-if="loading" :rows="3" animated />

    <ElEmpty v-else-if="failed" :description="error ?? '加载失败'">
      <ElButton size="small" @click="$emit('retry')">重试</ElButton>
    </ElEmpty>

    <ElEmpty v-else-if="empty" :description="emptyText ?? '暂无内容'" />

    <slot v-else />
  </div>
</template>

<style scoped>
.feed-state {
  min-height: 160px;
}

.feed-state :deep(.el-empty) {
  padding: var(--vctn-space-8) var(--vctn-space-4);
  border: 1px dashed var(--vctn-border);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
}

.feed-state :deep(.el-skeleton) {
  padding: var(--vctn-space-5);
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
}
</style>
