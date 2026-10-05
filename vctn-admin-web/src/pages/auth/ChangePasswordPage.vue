<script setup lang="ts">
/**
 * Forced password change.
 *
 * Reached when the backend reports `must_change_password`; the router guard
 * keeps the user here until it is done.
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCard, ElForm, ElFormItem, ElInput, type FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { renderError, toFormErrors } from '@/utils/error'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const submitting = ref(false)
const failureMessage = ref<string | null>(null)
const fieldErrors = ref<Record<string, string>>({})

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

async function onSubmit(): Promise<void> {
  submitting.value = true
  failureMessage.value = null
  fieldErrors.value = {}
  try {
    await authStore.changeOwnPassword(form.oldPassword, form.newPassword)
    await router.replace('/')
  } catch (error) {
    fieldErrors.value = toFormErrors(error)
    failureMessage.value = renderError(error).message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="change-password">
    <ElCard shadow="never" class="change-password__card">
      <h2 class="change-password__title">修改密码</h2>
      <ElAlert
        type="warning"
        :closable="false"
        show-icon
        title="首次登录或密码已过期"
        description="请先修改密码，之后才能访问其他页面。"
        class="change-password__notice"
      />
      <ElAlert
        v-if="failureMessage"
        type="error"
        :closable="false"
        show-icon
        :title="failureMessage"
        class="change-password__notice"
      />

      <ElForm :model="form" :rules="rules" label-width="100px" @submit.prevent="onSubmit">
        <ElFormItem label="当前密码" prop="oldPassword" :error="fieldErrors.old_password">
          <ElInput v-model="form.oldPassword" type="password" show-password autocomplete="off" />
        </ElFormItem>
        <ElFormItem label="新密码" prop="newPassword" :error="fieldErrors.new_password">
          <ElInput v-model="form.newPassword" type="password" show-password autocomplete="off" />
        </ElFormItem>
        <ElFormItem label="确认新密码" prop="confirmPassword">
          <ElInput v-model="form.confirmPassword" type="password" show-password autocomplete="off" />
        </ElFormItem>
        <div class="change-password__actions">
          <ElButton
            v-if="!authStore.mustChangePassword"
            @click="router.back()"
          >
            返回
          </ElButton>
          <ElButton type="primary" :loading="submitting" @click="onSubmit">提交</ElButton>
        </div>
      </ElForm>
    </ElCard>
  </div>
</template>

<style scoped>
.change-password {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.change-password__card {
  width: min(560px, 100%);
}

.change-password__title {
  margin: 0 0 16px;
  font-size: 18px;
}

.change-password__notice {
  margin-bottom: 16px;
}

.change-password__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
