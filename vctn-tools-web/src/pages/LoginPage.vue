<script setup lang="ts">
/**
 * Sign in / sign up.
 *
 * The portal itself is anonymous, so this page is entered on purpose — either
 * from the header or by a redirect guard. After a successful login the user is
 * taken back to where they came from (`?redirect=`), never to a dead end.
 */
import { computed, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { ApiEnvelopeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { LoginRequest, RegisterRequest } from '@/types/auth'

type Mode = 'login' | 'register'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = ref<Mode>('login')
const submitting = ref(false)

const loginForm = ref<LoginRequest>({ identity: '', password: '' })
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  nickname: '',
  email: '',
  phone: '',
})

const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()

const loginRules: FormRules<typeof loginForm.value> = {
  identity: [{ required: true, message: '请输入用户名 / 邮箱 / 手机号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const registerRules: FormRules<typeof registerForm.value> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度为 3–64 个字符', trigger: 'blur' },
    {
      pattern: /^[A-Za-z0-9_.-]+$/,
      message: '只能包含字母、数字、下划线、点和短横线',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        const password = String(value ?? '')
        const problems: string[] = []
        if (password.length < 12) {
          problems.push('至少 12 位')
        }
        if (!/[A-Z]/.test(password)) {
          problems.push('含大写字母')
        }
        if (!/[a-z]/.test(password)) {
          problems.push('含小写字母')
        }
        if (!/[0-9]/.test(password)) {
          problems.push('含数字')
        }
        if (!/[!@#$%^&*()\-_=+[\]{};:,.<>?/~\s]/.test(password)) {
          problems.push('含特殊字符')
        }
        if (problems.length > 0) {
          callback(new Error(`密码需${problems.join('、')}`))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    {
      validator: (_rule, value, callback) => {
        if (value !== registerForm.value.password) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  email: [
    {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: '邮箱格式不正确',
      trigger: 'blur',
    },
  ],
  phone: [
    {
      pattern: /^[0-9+\-() ]{5,32}$/,
      message: '手机号格式不正确',
      trigger: 'blur',
    },
  ],
}

/** Where to go afterwards — only same-site paths are honoured. */
const redirectTarget = computed(() => {
  const raw = route.query.redirect
  if (typeof raw === 'string' && raw.startsWith('/') && !raw.startsWith('//')) {
    return raw
  }
  return '/'
})

/** Surface the backend's own message, plus any itemised validation reasons. */
function describe(caught: unknown): string {
  if (caught instanceof ApiEnvelopeError) {
    if (Array.isArray(caught.details) && caught.details.length > 0) {
      return caught.details.map((item) => String(item)).join('；')
    }
    return caught.message
  }
  if (caught instanceof Error && caught.message !== '') {
    return caught.message
  }
  return '请求失败，请稍后重试'
}

async function submitLogin(): Promise<void> {
  const form = loginFormRef.value
  if (form === undefined) {
    return
  }
  const valid = await form.validate().catch(() => false)
  if (!valid) {
    return
  }
  submitting.value = true
  try {
    await auth.signIn({
      identity: loginForm.value.identity.trim(),
      password: loginForm.value.password,
    })
    ElMessage.success(`欢迎回来，${auth.displayName}`)
    void router.replace(redirectTarget.value)
  } catch (caught: unknown) {
    ElMessage.error(describe(caught))
  } finally {
    submitting.value = false
  }
}

async function submitRegister(): Promise<void> {
  const form = registerFormRef.value
  if (form === undefined) {
    return
  }
  const valid = await form.validate().catch(() => false)
  if (!valid) {
    return
  }
  const email = registerForm.value.email.trim()
  const phone = registerForm.value.phone.trim()
  // The backend builds a login identity from one of the two, so at least one
  // must be present — otherwise the account could never sign in again.
  if (email === '' && phone === '') {
    ElMessage.warning('邮箱和手机号请至少填写一个')
    return
  }
  submitting.value = true
  try {
    const payload: RegisterRequest = {
      username: registerForm.value.username.trim(),
      password: registerForm.value.password,
      nickname: registerForm.value.nickname.trim() === '' ? null : registerForm.value.nickname.trim(),
      email: email === '' ? null : email,
      phone: phone === '' ? null : phone,
    }
    await auth.signUp(payload)
    // Registration does not issue a session, so sign the new account straight
    // in rather than making the user retype what they just typed.
    await auth.signIn({ identity: payload.username, password: payload.password })
    ElMessage.success('注册成功，已自动登录')
    void router.replace(redirectTarget.value)
  } catch (caught: unknown) {
    ElMessage.error(describe(caught))
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
          <span class="login-page__title">VCTN Tools</span>
          <span class="login-page__subtitle">登录后可同步最近使用与用量记录；不登录也能使用全部工具</span>
        </div>
      </template>

      <ElTabs v-model="mode" class="login-page__tabs">
        <ElTabPane label="登录" name="login">
          <ElForm
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-position="top"
            @submit.prevent="submitLogin"
          >
            <ElFormItem label="用户名 / 邮箱 / 手机号" prop="identity">
              <ElInput
                v-model="loginForm.identity"
                placeholder="testuser"
                autocomplete="username"
                @keyup.enter="submitLogin"
              />
            </ElFormItem>
            <ElFormItem label="密码" prop="password">
              <ElInput
                v-model="loginForm.password"
                type="password"
                show-password
                autocomplete="current-password"
                @keyup.enter="submitLogin"
              />
            </ElFormItem>
            <ElButton type="primary" class="login-page__submit" :loading="submitting" @click="submitLogin">
              登录
            </ElButton>
          </ElForm>
        </ElTabPane>

        <ElTabPane label="注册" name="register">
          <ElForm
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-position="top"
            @submit.prevent="submitRegister"
          >
            <ElFormItem label="用户名" prop="username">
              <ElInput v-model="registerForm.username" placeholder="3–64 位，字母数字下划线" autocomplete="username" />
            </ElFormItem>
            <ElFormItem label="昵称" prop="nickname">
              <ElInput v-model="registerForm.nickname" placeholder="选填" />
            </ElFormItem>
            <ElFormItem label="邮箱" prop="email">
              <ElInput v-model="registerForm.email" placeholder="邮箱 / 手机号至少填一个" autocomplete="email" />
            </ElFormItem>
            <ElFormItem label="手机号" prop="phone">
              <ElInput v-model="registerForm.phone" placeholder="选填" autocomplete="tel" />
            </ElFormItem>
            <ElFormItem label="密码" prop="password">
              <ElInput
                v-model="registerForm.password"
                type="password"
                show-password
                autocomplete="new-password"
                placeholder="至少 12 位，含大小写字母、数字和特殊字符"
              />
            </ElFormItem>
            <ElFormItem label="确认密码" prop="confirmPassword">
              <ElInput
                v-model="registerForm.confirmPassword"
                type="password"
                show-password
                autocomplete="new-password"
                @keyup.enter="submitRegister"
              />
            </ElFormItem>
            <ElButton type="primary" class="login-page__submit" :loading="submitting" @click="submitRegister">
              注册并登录
            </ElButton>
          </ElForm>
        </ElTabPane>
      </ElTabs>

      <div class="login-page__footer">
        <RouterLink to="/">← 先随便逛逛</RouterLink>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  padding: var(--vctn-space-8) 0 var(--vctn-space-8);
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

.login-page__footer {
  margin-top: var(--vctn-space-4);
  font-size: var(--vctn-text-sm);
  text-align: center;
}

.login-page__footer a {
  color: var(--vctn-text-secondary);
  text-decoration: none;
}

.login-page__footer a:hover {
  color: var(--vctn-brand);
}
</style>
