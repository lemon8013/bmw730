<script setup lang="ts">
/**
 * A small line chart drawn as inline SVG.
 *
 * Used for the page-view / unique-visitor trend; dependency free for the same
 * reason as `BarChart`.
 */
import { computed } from 'vue'

interface Point {
  label: string
  value: number
}

interface Props {
  points: readonly Point[]
  /** Accessible description of what the line represents. */
  seriesName: string
  color?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), { color: '#409eff', height: 160 })

const geometry = computed(() => {
  if (props.points.length === 0) {
    return null
  }
  const values = props.points.map((point) => point.value)
  const maximum = Math.max(...values, 1)
  const step = props.points.length > 1 ? 100 / (props.points.length - 1) : 0
  const coordinates = props.points.map((point, index) => ({
    x: props.points.length > 1 ? index * step : 50,
    y: 100 - (point.value / maximum) * 100,
    point,
  }))
  const path = coordinates
    .map((item, index) => `${index === 0 ? 'M' : 'L'}${item.x.toFixed(2)},${item.y.toFixed(2)}`)
    .join(' ')
  return { coordinates, path, maximum }
})
</script>

<template>
  <div class="line-chart">
    <p v-if="geometry === null" class="line-chart__empty">暂无数据</p>
    <div v-else>
      <svg
        class="line-chart__svg"
        :viewBox="`0 0 100 100`"
        preserveAspectRatio="none"
        :style="{ height: `${height}px` }"
        role="img"
        :aria-label="seriesName"
      >
        <line x1="0" y1="100" x2="100" y2="100" stroke="var(--vctn-border)" stroke-width="0.4" />
        <line x1="0" y1="50" x2="100" y2="50" stroke="var(--vctn-border-subtle)" stroke-width="0.3" />
        <path
          :d="geometry.path"
          fill="none"
          :stroke="color"
          stroke-width="1.2"
          vector-effect="non-scaling-stroke"
        />
        <circle
          v-for="item in geometry.coordinates"
          :key="`${item.point.label}`"
          :cx="item.x"
          :cy="item.y"
          r="1.2"
          :fill="color"
          vector-effect="non-scaling-stroke"
        />
      </svg>
      <div class="line-chart__axis">
        <span>{{ points[0]?.label }}</span>
        <span v-if="geometry.maximum > 0">峰值 {{ geometry.maximum }}</span>
        <span>{{ points[points.length - 1]?.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.line-chart__empty {
  margin: 0;
  padding: 24px 0;
  color: var(--vctn-text-secondary);
  text-align: center;
}

.line-chart__svg {
  display: block;
  width: 100%;
}

.line-chart__axis {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  color: var(--vctn-text-secondary);
  font-size: 12px;
}
</style>
