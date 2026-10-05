<script setup lang="ts">
/**
 * A small horizontal bar chart drawn as inline SVG.
 *
 * Deliberately dependency free: the frozen dependency index lists a charting
 * library, but the console only needs ranked value comparison, and drawing it
 * here keeps the bundle honest and the labels accessible.
 */
import { computed } from 'vue'

interface Bar {
  label: string
  value: number
  /** Optional secondary value shown next to the primary one. */
  secondary?: number
}

interface Props {
  bars: readonly Bar[]
  /** Value used to scale the bars; defaults to the largest bar. */
  max?: number
  /** Rendered when every value is zero. */
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), { max: undefined, emptyText: '暂无数据' })

const ceiling = computed(() => {
  if (props.max !== undefined && props.max > 0) {
    return props.max
  }
  const largest = props.bars.reduce((current, bar) => Math.max(current, bar.value), 0)
  return largest > 0 ? largest : 1
})

const hasData = computed(() => props.bars.some((bar) => bar.value > 0))

function widthOf(value: number): string {
  const ratio = Math.min(1, Math.max(0, value / ceiling.value))
  return `${(ratio * 100).toFixed(2)}%`
}
</script>

<template>
  <div class="bar-chart">
    <p v-if="!hasData" class="bar-chart__empty">{{ emptyText }}</p>
    <ul v-else class="bar-chart__list">
      <li v-for="bar in bars" :key="bar.label" class="bar-chart__row">
        <span class="bar-chart__label" :title="bar.label">{{ bar.label }}</span>
        <span class="bar-chart__track">
          <span class="bar-chart__fill" :style="{ width: widthOf(bar.value) }" />
        </span>
        <span class="bar-chart__value">
          {{ bar.value }}
          <small v-if="bar.secondary !== undefined" class="bar-chart__secondary">
            / {{ bar.secondary }}
          </small>
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.bar-chart__empty {
  margin: 0;
  padding: 24px 0;
  color: var(--el-text-color-secondary);
  text-align: center;
}

.bar-chart__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.bar-chart__row {
  display: grid;
  grid-template-columns: minmax(80px, 160px) 1fr minmax(64px, auto);
  gap: 12px;
  align-items: center;
  padding: 4px 0;
}

.bar-chart__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.bar-chart__track {
  height: 10px;
  overflow: hidden;
  border-radius: 5px;
  background-color: var(--el-fill-color);
}

.bar-chart__fill {
  display: block;
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--el-color-primary), var(--el-color-primary-light-3));
}

.bar-chart__value {
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  text-align: right;
}

.bar-chart__secondary {
  color: var(--el-text-color-secondary);
}
</style>
