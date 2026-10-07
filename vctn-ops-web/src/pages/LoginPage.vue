<script setup lang="ts">
/**
 * Sign in.
 *
 * The console is the one VCTN frontend that is useless without a session, so
 * `/login` is the landing route for a signed-out visitor and everything else
 * redirects here with `?redirect=`. The return URL is restricted to a
 * same-site path: an open redirect would let a crafted link move a freshly
 * authenticated operator onto another origin.
 */
import { computed, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { renderError } from '@/utils/error'
import type { LoginRequest } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const submitting = ref(false)
const form = ref<LoginRequest>({ username: '', password: '' })
const formRef = ref<FormInstance>()

const rules: FormRules<typeof form.value> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

/** Where to go afterwards — only same-site paths are honoured. */
const redirectTarget = computed(() => {
  const raw = route.query.redirect
  if (typeof raw === 'string' && raw.startsWith('/') && !raw.startsWith('//')) {
    return raw
  }
  return '/'
})

async function submit(): Promise<void> {
  const instance = formRef.value
  if (instance === undefined) {
    return
  }
  const valid = await instance.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    await auth.signIn({
      username: form.value.username.trim(),
      password: form.value.password,
    })
    ElMessage.success(`欢迎回来，${auth.displayName || auth.username}`)
    void router.replace(redirectTarget.value)
  } catch (caught: unknown) {
    // Surface the backend's own message: it is written for the operator and it
    // is the same sentence whether the username or the password was wrong.
    ElMessage.error(renderError(caught).message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <ElCard class="login-page__card" shadow="never">
      <template #header>
        <div class="login-page__header">
          <span class="login-page__title">VCTN 运维监控</span>
          <span class="login-page__subtitle">使用管理平台的管理员账号登录</span>
        </div>
      </template>

      <ElForm
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="submit"
      >
        <ElFormItem label="用户名" prop="username">
          <ElInput
            v-model="form.username"
            placeholder="admin"
            autocomplete="username"
            @keyup.enter="submit"
          />
        </ElFormItem>
        <ElFormItem label="密码" prop="password">
          <ElInput
            v-model="form.password"
            type="password"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </ElFormItem>
        <ElButton type="primary" class="login-page__submit" :loading="submitting" @click="submit">
          登录
        </ElButton>
      </ElForm>
    </ElCard>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  padding: var(--vctn-space-8) 0;
}

.login-page__card {
  width: 100%;
  max-width: 420px;
  border-radius: var(--vctn-radius-xl);
  box-shadow: var(--vctn-shadow-md);
}

.login-page__header {
  display: flex;
  flex-direction: column;
  gap: var(--vctn-space-1);
}

.login-page__title {
  color: var(--vctn-text-strong);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.login-page__subtitle {
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
  line-height: 1.6;
}

.login-page__submit {
  width: 100%;
  height: 40px;
}
</style>
