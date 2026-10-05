<script setup lang="ts">
/**
 * The console's one form shell.
 *
 * Owns the submit / reset / busy / error cycle and forwards validation to the
 * inner Element Plus form, so every page reports failures the same way. Field
 * level messages returned by the backend are merged into the model's rules by
 * the caller through `fieldErrors`.
 */
import { ref, watch } from 'vue'
import { ElAlert, ElButton, ElForm, type FormInstance, type FormRules } from 'element-plus'

interface Props {
  /** Bound model object; mutated in place by the fields inside the slot. */
  model: Record<string, unknown>
  rules?: FormRules
  labelWidth?: string
  loading?: boolean
  /** Failure message rendered above the fields. */
  errorMessage?: string | null
  /** Trace id of the last failure, shown to help support. */
  errorTraceId?: string | null
  submitText?: string
  resetText?: string
  showReset?: boolean
  /** Hide the footer, e.g. when the dialog provides the buttons. */
  hideFooter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  rules: undefined,
  labelWidth: '120px',
  loading: false,
  errorMessage: null,
  errorTraceId: null,
  submitText: '保存',
  resetText: '重置',
  showReset: true,
  hideFooter: false,
})

const emit = defineEmits<{ submit: []; reset: [] }>()

const formRef = ref<FormInstance>()

/** Validate the inner form; resolves `false` when the model is invalid. */
async function validate(): Promise<boolean> {
  const form = formRef.value
  if (form === undefined) {
    return true
  }
  try {
    await form.validate()
    return true
  } catch {
    return false
  }
}

/** Clear every validation message. */
function clearValidation(): void {
  formRef.value?.clearValidate()
}

/** Re-validate when the backend reports field errors. */
watch(
  () => props.errorMessage,
  () => {
    void formRef.value?.validate().catch(() => undefined)
  },
)

async function onSubmit(): Promise<void> {
  if (props.loading) {
    return
  }
  if (!(await validate())) {
    return
  }
  emit('submit')
}

function onReset(): void {
  clearValidation()
  emit('reset')
}

defineExpose({ validate, clearValidation })
</script>

<template>
  <ElForm
    ref="formRef"
    :model="model"
    :rules="rules"
    :label-width="labelWidth"
    :disabled="loading"
    label-position="right"
    class="base-form"
  >
    <ElAlert
      v-if="errorMessage"
      type="error"
      :closable="false"
      show-icon
      title="提交失败"
      :description="errorMessage"
      class="base-form__error"
    />
    <p v-if="errorTraceId" class="base-form__trace">Trace ID: {{ errorTraceId }}</p>

    <slot />

    <div v-if="!hideFooter" class="base-form__footer">
      <ElButton v-if="showReset" @click="onReset">{{ resetText }}</ElButton>
      <ElButton type="primary" :loading="loading" @click="onSubmit">{{ submitText }}</ElButton>
    </div>
  </ElForm>
</template>

<style scoped>
.base-form__error {
  margin-bottom: 16px;
}

.base-form__trace {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.base-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
