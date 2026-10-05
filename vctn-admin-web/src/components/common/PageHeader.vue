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
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header__text {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.page-header__tag {
  margin-left: 8px;
  vertical-align: middle;
}

.page-header__description {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.page-header__actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
