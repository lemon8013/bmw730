<script setup lang="ts">
/**
 * The console's one dialog.
 *
 * Guarantees a scrollable body on short screens, a stable width on wide ones,
 * an explicit cancel button and a confirming button that cannot be pressed
 * twice while the request is in flight.
 */
import { ElButton, ElDialog } from 'element-plus'

interface Props {
  modelValue: boolean
  title: string
  width?: string | number
  /** Disable the confirming button (e.g. while the form is invalid). */
  confirmDisabled?: boolean
  /** Show the busy state on the confirming button. */
  confirmLoading?: boolean
  confirmText?: string
  cancelText?: string
  /** Hide the footer entirely, for pure content dialogs. */
  hideFooter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  width: '560px',
  confirmDisabled: false,
  confirmLoading: false,
  confirmText: '确定',
  cancelText: '取消',
  hideFooter: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  cancel: []
}>()

function close(): void {
  emit('update:modelValue', false)
}

function onConfirm(): void {
  if (props.confirmDisabled || props.confirmLoading) {
    return
  }
  emit('confirm')
}

function onCancel(): void {
  emit('cancel')
  close()
}
</script>

<template>
  <ElDialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    append-to-body
    destroy-on-close
    :close-on-click-modal="false"
    class="base-dialog"
    @update:model-value="emit('update:modelValue', $event)"
    @closed="onCancel"
  >
    <div class="base-dialog__body">
      <slot />
    </div>

    <template v-if="!hideFooter" #footer>
      <ElButton @click="close">{{ cancelText }}</ElButton>
      <ElButton type="primary" :disabled="confirmDisabled" :loading="confirmLoading" @click="onConfirm">
        {{ confirmText }}
      </ElButton>
    </template>
  </ElDialog>
</template>

<style scoped>
.base-dialog__body {
  max-height: min(70vh, 640px);
  overflow-y: auto;
}
</style>
