<script setup lang="ts">
/**
 * Column visibility and ordering panel for one table.
 *
 * Rendered inside a popover from `BaseTable`. Ordering is offered both as
 * drag-and-drop and as explicit move buttons, so it stays usable with a
 * keyboard and does not depend on a drag library that is not in the frozen
 * dependency index.
 */
import { computed, ref } from 'vue'
import { ElButton, ElCheckbox, ElEmpty, ElIcon, ElTooltip } from 'element-plus'
import { ArrowDown, ArrowUp, Rank, Refresh } from '@element-plus/icons-vue'

import type { TableColumnMeta, TableSettings } from '@/components/table/column-settings'

interface Props {
  columns: readonly TableColumnMeta[]
  settings: TableSettings
}

const props = defineProps<Props>()

const emit = defineEmits<{ update: [settings: TableSettings] }>()

const dragKey = ref<string | null>(null)

/** Columns in the order the user arranged them. */
const orderedColumns = computed<TableColumnMeta[]>(() => {
  const position = new Map(props.settings.order.map((key, index) => [key, index]))
  return [...props.columns].sort(
    (left, right) =>
      (position.get(left.key) ?? Number.MAX_SAFE_INTEGER) -
      (position.get(right.key) ?? Number.MAX_SAFE_INTEGER),
  )
})

const hiddenSet = computed(() => new Set(props.settings.hidden))

const visibleCount = computed(() => props.columns.length - hiddenSet.value.size)

function isVisible(key: string): boolean {
  return !hiddenSet.value.has(key)
}

function commit(order: string[], hidden: readonly string[]): void {
  emit('update', { order, hidden: [...hidden] })
}

function onToggle(key: string, visible: boolean): void {
  const hidden = new Set(props.settings.hidden)
  if (visible) {
    hidden.delete(key)
  } else {
    hidden.add(key)
  }
  commit(orderedColumns.value.map((column) => column.key), [...hidden])
}

function move(key: string, offset: number): void {
  const order = orderedColumns.value.map((column) => column.key)
  const from = order.indexOf(key)
  const to = from + offset
  if (from === -1 || to < 0 || to >= order.length) {
    return
  }
  const [moved] = order.splice(from, 1)
  if (moved === undefined) {
    return
  }
  order.splice(to, 0, moved)
  commit(order, props.settings.hidden)
}

function onDragStart(key: string): void {
  dragKey.value = key
}

function onDrop(target: string): void {
  const source = dragKey.value
  dragKey.value = null
  if (source === null || source === target) {
    return
  }
  const order = orderedColumns.value.map((column) => column.key)
  const from = order.indexOf(source)
  const to = order.indexOf(target)
  if (from === -1 || to === -1) {
    return
  }
  const [moved] = order.splice(from, 1)
  if (moved === undefined) {
    return
  }
  order.splice(to, 0, moved)
  commit(order, props.settings.hidden)
}

function showAll(): void {
  commit(
    orderedColumns.value.map((column) => column.key),
    [],
  )
}

function reset(): void {
  commit(
    props.columns.map((column) => column.key),
    [],
  )
}
</script>

<template>
  <div class="column-settings">
    <header class="column-settings__header">
      <span class="column-settings__title">列设置</span>
      <span class="column-settings__count">{{ visibleCount }} / {{ columns.length }}</span>
    </header>

    <ElEmpty v-if="columns.length === 0" description="该表格没有可配置的列" :image-size="48" />

    <ul v-else class="column-settings__list">
      <li
        v-for="(column, index) in orderedColumns"
        :key="column.key"
        class="column-settings__item"
        :class="{ 'column-settings__item--dragging': dragKey === column.key }"
        draggable="true"
        @dragstart="onDragStart(column.key)"
        @dragover.prevent
        @drop="onDrop(column.key)"
      >
        <ElIcon class="column-settings__handle"><Rank /></ElIcon>

        <ElCheckbox
          :model-value="isVisible(column.key)"
          class="column-settings__checkbox"
          @update:model-value="onToggle(column.key, $event === true)"
        >
          {{ column.label }}
        </ElCheckbox>

        <span class="column-settings__actions">
          <ElTooltip content="上移" placement="top">
            <ElButton
              text
              size="small"
              :disabled="index === 0"
              @click="move(column.key, -1)"
            >
              <ElIcon><ArrowUp /></ElIcon>
            </ElButton>
          </ElTooltip>
          <ElTooltip content="下移" placement="top">
            <ElButton
              text
              size="small"
              :disabled="index === orderedColumns.length - 1"
              @click="move(column.key, 1)"
            >
              <ElIcon><ArrowDown /></ElIcon>
            </ElButton>
          </ElTooltip>
        </span>
      </li>
    </ul>

    <footer class="column-settings__footer">
      <ElButton text size="small" @click="showAll">全部显示</ElButton>
      <ElButton text size="small" @click="reset">
        <ElIcon><Refresh /></ElIcon>
        <span class="column-settings__reset">恢复默认</span>
      </ElButton>
    </footer>
  </div>
</template>

<style scoped>
.column-settings {
  width: 260px;
}

.column-settings__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.column-settings__title {
  font-weight: 600;
}

.column-settings__count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.column-settings__list {
  max-height: 320px;
  margin: 4px 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.column-settings__item {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 2px 0;
  border-radius: 4px;
}

.column-settings__item:hover {
  background-color: var(--el-fill-color-light);
}

.column-settings__item--dragging {
  opacity: 0.5;
}

.column-settings__handle {
  color: var(--el-text-color-placeholder);
  cursor: grab;
}

.column-settings__checkbox {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.column-settings__actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
}

.column-settings__footer {
  display: flex;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.column-settings__reset {
  margin-left: 4px;
}
</style>
