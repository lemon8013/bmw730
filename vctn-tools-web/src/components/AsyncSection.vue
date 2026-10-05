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
  gap: 10px;
  padding: 40px 0;
  color: var(--el-text-color-secondary);
}

.async-section__spinner {
  font-size: 22px;
  color: var(--el-color-primary);
}

.async-section__error {
  color: var(--el-color-danger);
}
</style>
