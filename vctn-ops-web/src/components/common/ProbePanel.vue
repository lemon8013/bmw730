<script setup lang="ts">
/**
 * One collector reading.
 *
 * Every PostgreSQL and Redis reading shares the same degradation envelope:
 * when the probe fails the metric fields stay `null`, `status` becomes
 * `UNKNOWN` and `error` carries the reason — so the page shows a "collection
 * failed" panel instead of an HTTP error.
 */
import { computed } from 'vue'
import { ElAlert, ElTag } from 'element-plus'

import type { ProbeResult } from '@/types/ops'
import { formatDateTime } from '@/utils/format'

interface Props {
  title: string
  /** The reading, or `null` while it has not arrived yet. */
  reading: ProbeResult | null
}

const props = defineProps<Props>()

const degraded = computed(() => props.reading !== null && props.reading.status !== 'UP')
</script>

<template>
  <section class="probe-panel vctn-panel">
    <header class="probe-panel__header">
      <h3 class="probe-panel__title">{{ title }}</h3>
      <ElTag v-if="reading" :type="degraded ? 'warning' : 'success'" size="small" effect="light">
        {{ reading.status }}
      </ElTag>
    </header>

    <ElAlert
      v-if="degraded && reading"
      type="warning"
      :closable="false"
      show-icon
      title="采集失败"
      :description="reading.error ?? '后端未能完成本次采集'"
      class="probe-panel__alert"
    />

    <slot v-if="!degraded" />

    <p v-if="reading" class="probe-panel__collected vctn-muted">
      采集时间 {{ formatDateTime(reading.collected_at) }}
    </p>
  </section>
</template>

<style scoped>
.probe-panel__header {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-2);
  margin-bottom: var(--vctn-space-3);
}

.probe-panel__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-base);
  font-weight: 500;
}

.probe-panel__alert {
  margin-bottom: var(--vctn-space-3);
}

.probe-panel__collected {
  margin-top: var(--vctn-space-3);
}
</style>
