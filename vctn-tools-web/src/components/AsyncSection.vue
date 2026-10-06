<script setup lang="ts">
/** Shared loading / failure / empty wrapper for one async section. */
import { ElButton, ElEmpty, ElIcon } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    loading?: boolean
    failed?: boolean
    error?: string | null
    empty?: boolean
    emptyText?: string
  }>(),
  {
    loading: false,
    failed: false,
    error: null,
    empty: false,
    emptyText: '暂无数据',
  },
)

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="loading" class="async-section async-section--state">
    <ElIcon class="async-section__spinner is-loading"><Loading /></ElIcon>
    <span>加载中…</span>
  </div>

  <div v-else-if="failed" class="async-section async-section--state">
    <span class="async-section__error">{{ error ?? '加载失败' }}</span>
    <ElButton size="small" @click="emit('retry')">重试</ElButton>
  </div>

  <ElEmpty v-else-if="empty" :description="emptyText" />

  <slot v-else />
</template>

<style scoped>
.async-section--state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--vctn-space-2);
  padding: var(--vctn-space-8) var(--vctn-space-4);
  border: 1px dashed var(--vctn-border);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  color: var(--vctn-text-secondary);
}

.async-section__spinner {
  font-size: 22px;
  color: var(--vctn-brand);
}

.async-section__error {
  color: var(--vctn-danger);
}
</style>
