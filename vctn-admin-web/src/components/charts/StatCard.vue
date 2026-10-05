<script setup lang="ts">
/** One dashboard metric. */
interface Props {
  label: string
  value: string | number
  hint?: string
}

withDefaults(defineProps<Props>(), { hint: undefined })
</script>

<template>
  <div class="stat-card">
    <p class="stat-card__label">{{ label }}</p>
    <p class="stat-card__value">{{ value }}</p>
    <p v-if="hint" class="stat-card__hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.stat-card {
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  background-color: var(--el-bg-color);
}

.stat-card__label {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stat-card__value {
  margin: 8px 0 0;
  font-size: 24px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.stat-card__hint {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
