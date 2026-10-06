<script setup lang="ts">
/** Administrator sign in. */
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton, ElCard, ElForm, ElFormItem, ElInput, type FormRules } from 'element-plus'

import { safeReturnPath } from '@/router/guards'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import { renderError } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const permissionStore = usePermissionStore()

const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const submitting = ref(false)
const failureMessage = ref<string | null>(null)
const failureTraceId = ref<string | null>(null)

const versionLabel = computed(() => `v${appStore.version}`)

async function onSubmit(): Promise<void> {
  submitting.value = true
  failureMessage.value = null
  failureTraceId.value = null
  try {
    await authStore.signIn({ username: form.username, password: form.password })
    const requested = safeReturnPath(route.query.redirect)
    const target = requested ?? permissionStore.landingPath
    await router.replace(target === '/' ? '/' : target)
  } catch (error) {
    const rendered = renderError(error)
    failureMessage.value = rendered.message
    failureTraceId.value = rendered.traceId ?? null
    // The password is never kept after a failed attempt.
    form.password = ''
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login">
    <ElCard class="login__card" shadow="never">
      <div class="login__brand">
        <span class="login__mark">V</span>
        <div>
          <h1 class="login__title">{{ appStore.applicationName }}</h1>
          <p class="login__subtitle">{{ versionLabel }}</p>
        </div>
      </div>

      <ElAlert
        v-if="failureMessage"
        type="error"
        :closable="false"
        show-icon
        :title="failureMessage"
        class="login__alert"
      />
      <p v-if="failureTraceId" class="login__trace">Trace ID: {{ failureTraceId }}</p>

      <ElForm :model="form" :rules="rules" label-position="top" @submit.prevent="onSubmit">
        <ElFormItem label="用户名" prop="username">
          <ElInput
            v-model="form.username"
            placeholder="请输入管理员用户名"
            autocomplete="username"
            clearable
          />
        </ElFormItem>
        <ElFormItem label="密码" prop="password">
          <ElInput
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
            @keyup.enter="onSubmit"
          />
        </ElFormItem>
        <ElButton type="primary" class="login__submit" :loading="submitting" @click="onSubmit">
          登录
        </ElButton>
      </ElForm>

      <p class="login__hint">
        登录请求会携带 X-Trace-ID 与 X-Request-ID，失败时可在上方获取 Trace ID 以便排查。
      </p>
    </ElCard>
  </div>
</template>

<style scoped>
.login {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100vh;
  padding: var(--vctn-space-6);
  background: linear-gradient(135deg, var(--vctn-brand-softer) 0%, var(--vctn-bg-page) 55%);
  transition: background var(--vctn-duration-base) var(--vctn-ease);
}

.login__card {
  width: min(420px, 100%);
  border-radius: var(--vctn-radius-xl);
  box-shadow: var(--vctn-shadow-lg);
}

.login__brand {
  display: flex;
  gap: var(--vctn-space-3);
  align-items: center;
  margin-bottom: var(--vctn-space-5);
}

.login__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: var(--vctn-radius-md);
  background-color: var(--vctn-brand);
  color: var(--vctn-text-inverse);
  font-size: var(--vctn-text-xl);
  font-weight: 500;
  letter-spacing: 0.02em;
}

.login__title {
  margin: 0;
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-xl);
  font-weight: 500;
  letter-spacing: -0.01em;
}

.login__subtitle {
  margin: 2px 0 0;
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
}

.login__alert {
  margin-bottom: var(--vctn-space-3);
}

.login__trace {
  margin: 0 0 var(--vctn-space-3);
  color: var(--vctn-text-secondary);
  font-family: var(--vctn-font-mono);
  font-size: var(--vctn-text-xs);
  word-break: break-all;
}

.login__submit {
  width: 100%;
  height: 40px;
}

.login__hint {
  margin: var(--vctn-space-4) 0 0;
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
  line-height: 1.6;
}
</style>
