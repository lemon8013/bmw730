<script setup lang="ts">
/**
 * Picks one platform business user.
 *
 * Growth, points, tasks and every other gamification read is per **business
 * user**, while the console signs in as an operator. Every page therefore needs
 * "which user am I looking at", and doing it six times differently would drift.
 * The picker searches remotely so a deployment with thousands of users does not
 * load them all into the DOM.
 */
import { ref, watch } from 'vue'
import { ElOption, ElSelect } from 'element-plus'

import { listBizUsers } from '@/api/growth'
import type { BizUserBrief } from '@/types/growth'
import { renderError } from '@/utils/error'

const props = withDefaults(
  defineProps<{
    /** Currently selected user id; empty string means "none". */
    modelValue?: string
    /** Rendered when nothing is selected. */
    placeholder?: string
    /** Native width passed to the select. */
    width?: string
  }>(),
  {
    modelValue: '',
    placeholder: '选择业务用户',
    width: '280px',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', user: BizUserBrief | null): void
}>()

const options = ref<BizUserBrief[]>([])
const loading = ref(false)
const error = ref('')

async function search(keyword: string): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const page = await listBizUsers({ keyword: keyword || null, page: 1, page_size: 20 })
    options.value = page.items
    // Keep the selected user visible even when the search excludes it.
    if (props.modelValue && !page.items.some((row) => row.user_id === props.modelValue)) {
      const all = await listBizUsers({ keyword: props.modelValue, page: 1, page_size: 5 })
      const hit = all.items.find((row) => row.user_id === props.modelValue)
      if (hit) {
        options.value = [hit, ...page.items]
      }
    }
  } catch (caught) {
    error.value = renderError(caught).message
  } finally {
    loading.value = false
  }
}

void search('')

function onChange(value: string): void {
  emit('update:modelValue', value ?? '')
  emit('change', options.value.find((row) => row.user_id === value) ?? null)
}

watch(
  () => props.modelValue,
  (value) => {
    if (value && !options.value.some((row) => row.user_id === value)) {
      void search('')
    }
  },
)

defineExpose({ search })
</script>

<template>
  <div class="biz-user-picker">
    <ElSelect
      :model-value="modelValue"
      filterable
      remote
      clearable
      reserve-keyword
      :remote-method="search"
      :loading="loading"
      :placeholder="error || placeholder"
      :style="{ width }"
      @change="onChange"
    >
      <ElOption
        v-for="row in options"
        :key="row.user_id"
        :label="row.nickname || row.username || row.user_id"
        :value="row.user_id"
      >
        <span>{{ row.nickname || row.username }}</span>
        <span class="biz-user-picker__meta">
          {{ row.username ? `@${row.username}` : row.user_id }}
        </span>
      </ElOption>
    </ElSelect>
  </div>
</template>

<style scoped>
.biz-user-picker__meta {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
