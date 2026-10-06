<script setup lang="ts">
/** One workbench input field, driven by a ToolFieldDescriptor. */
import { computed } from 'vue'
import { ElInput, ElInputNumber, ElOption, ElSelect, ElSwitch } from 'element-plus'

import type { ToolFieldDescriptor } from '@/types/tool'

const props = defineProps<{
  descriptor: ToolFieldDescriptor
  /** Values of all fields, used to evaluate `showWhen`. */
  allValues: Record<string, unknown>
}>()

const value = defineModel<string | number | boolean>({ required: true })

const visible = computed(() => {
  const rule = props.descriptor.showWhen
  if (rule === undefined) {
    return true
  }
  return rule.equals.includes(String(props.allValues[rule.field] ?? ''))
})
</script>

<template>
  <div v-if="visible" class="field-input">
    <div class="field-input__label">
      {{ descriptor.label }}
      <span v-if="descriptor.required" class="field-input__required">*</span>
    </div>

    <ElInput
      v-if="descriptor.kind === 'textarea'"
      v-model="value as string"
      type="textarea"
      :rows="8"
      :placeholder="descriptor.placeholder"
    />
    <ElInput
      v-else-if="descriptor.kind === 'text'"
      v-model="value as string"
      :placeholder="descriptor.placeholder"
      clearable
    />
    <ElInputNumber
      v-else-if="descriptor.kind === 'number'"
      v-model="value as number"
      :min="descriptor.min"
      :max="descriptor.max"
      style="width: 200px"
    />
    <ElSelect
      v-else-if="descriptor.kind === 'select'"
      v-model="value as string"
      style="width: 280px"
    >
      <ElOption
        v-for="option in descriptor.options ?? []"
        :key="option.value"
        :label="option.label"
        :value="option.value"
      />
    </ElSelect>
    <ElSwitch v-else-if="descriptor.kind === 'switch'" v-model="value as boolean" />

    <div v-if="descriptor.help !== undefined" class="field-input__help">
      {{ descriptor.help }}
    </div>
  </div>
</template>

<style scoped>
.field-input {
  margin-bottom: var(--vctn-space-4);
}

.field-input__label {
  margin-bottom: var(--vctn-space-2);
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-sm);
  font-weight: 500;
}

.field-input__required {
  margin-left: 2px;
  color: var(--vctn-danger);
}

.field-input__help {
  margin-top: var(--vctn-space-2);
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
  line-height: 1.6;
}
</style>
