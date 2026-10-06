<script setup lang="ts">
/** Self service password change. */
import { reactive, ref } from 'vue'
import { ElForm, ElFormItem, ElInput, type FormRules } from 'element-plus'

import BaseDialog from '@/components/dialog/BaseDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'
import { toFormErrors } from '@/utils/error'

interface Props {
  modelValue: boolean
}

defineProps<Props>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const authStore = useAuthStore()
const notify = useConfirm()

const form = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const errorTraceId = ref<string | null>(null)

const rules: FormRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '新密码至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback: (error?: Error) => void) => {
        if (value !== form.newPassword) {
          callback(new Error('两次输入的新密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

function close(): void {
  emit('update:modelValue', false)
}

async function onSubmit(): Promise<void> {
  submitting.value = true
  errorMessage.value = null
  errorTraceId.value = null
  try {
    await authStore.changeOwnPassword(form.oldPassword, form.newPassword)
    notify.success('密码已更新')
    form.oldPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
    close()
  } catch (error) {
    const fieldErrors = toFormErrors(error)
    errorMessage.value = fieldErrors.new_password ?? (error as Error).message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <BaseDialog
    :model-value="modelValue"
    title="修改密码"
    width="480px"
    :confirm-loading="submitting"
    confirm-text="提交"
    @update:model-value="emit('update:modelValue', $event)"
    @confirm="onSubmit"
  >
    <ElForm :model="form" :rules="rules" label-width="100px">
      <ElFormItem label="当前密码" prop="oldPassword">
        <ElInput v-model="form.oldPassword" type="password" show-password autocomplete="off" />
      </ElFormItem>
      <ElFormItem label="新密码" prop="newPassword">
        <ElInput v-model="form.newPassword" type="password" show-password autocomplete="off" />
      </ElFormItem>
      <ElFormItem label="确认新密码" prop="confirmPassword">
        <ElInput v-model="form.confirmPassword" type="password" show-password autocomplete="off" />
      </ElFormItem>
      <p v-if="errorMessage" class="change-password__error">{{ errorMessage }}</p>
      <p v-if="errorTraceId" class="change-password__trace">Trace ID: {{ errorTraceId }}</p>
    </ElForm>
  </BaseDialog>
</template>

<style scoped>
.change-password__error {
  margin: 0;
  color: var(--vctn-danger);
  font-size: 13px;
}

.change-password__trace {
  margin: 4px 0 0;
  color: var(--vctn-text-secondary);
  font-family: monospace;
  font-size: 12px;
}
</style>
