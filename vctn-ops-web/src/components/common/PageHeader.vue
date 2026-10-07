<script setup lang="ts">
/** Page title, optional description, and the action area on the right. */
import { ElTag } from 'element-plus'

interface Props {
  title: string
  description?: string
  /** Optional status chip, e.g. a record status. */
  tagText?: string
  tagType?: 'primary' | 'success' | 'info' | 'warning' | 'danger'
}

withDefaults(defineProps<Props>(), {
  description: undefined,
  tagText: undefined,
  tagType: 'info',
})
</script>

<template>
  <header class="page-header">
    <div class="page-header__text">
      <h2 class="page-header__title">
        {{ title }}
        <ElTag v-if="tagText" :type="tagType" size="small" class="page-header__tag">
          {{ tagText }}
        </ElTag>
      </h2>
      <p v-if="description" class="page-header__description">{{ description }}</p>
    </div>
    <div class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-3);
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: var(--vctn-space-4);
  margin-bottom: var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.page-header__text {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.page-header__tag {
  margin-left: var(--vctn-space-2);
  vertical-align: middle;
}

.page-header__description {
  margin: var(--vctn-space-1) 0 0;
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
}

.page-header__actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: var(--vctn-space-2);
}
</style>
