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
  padding: var(--vctn-space-4);
  border: 1px solid var(--vctn-border);
  border-radius: var(--vctn-radius-lg);
  background-color: var(--vctn-bg-surface);
  box-shadow: var(--vctn-shadow-xs);
  transition:
    border-color var(--vctn-duration-base) var(--vctn-ease),
    box-shadow var(--vctn-duration-base) var(--vctn-ease);
}

.stat-card:hover {
  border-color: var(--vctn-border-brand);
  box-shadow: var(--vctn-shadow-sm);
}

.stat-card__label {
  margin: 0;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-xs);
}

.stat-card__value {
  margin: var(--vctn-space-2) 0 0;
  color: var(--vctn-text-strong);
  font-size: 28px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.stat-card__hint {
  margin: var(--vctn-space-1) 0 0;
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}
</style>
