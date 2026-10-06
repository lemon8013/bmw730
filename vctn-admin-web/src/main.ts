/**
 * Application entry point.
 *
 * Boot order matters: the router exists before the session is restored, and the
 * dynamic routes are installed as soon as the permission projection changes —
 * so a deep link is resolved against the real menu rather than against a
 * placeholder.
 */

import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { createApp, watch } from 'vue'

import 'element-plus/dist/index.css'
import '@/styles/tokens.css'
import '@/styles/index.css'

import App from '@/App.vue'
import { registerDirectives } from '@/directives'
import { createAppRouter, installDynamicRoutes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'

const app = createApp(App)
const pinia = createPinia()
const router = createAppRouter()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

registerDirectives(app)

const authStore = useAuthStore(pinia)
const permissionStore = usePermissionStore(pinia)

authStore.bindSessionExpiry()

// Re-install the contributed routes whenever the backend grants a new set.
watch(
  () => permissionStore.routeRecords,
  (records) => {
    installDynamicRoutes(router, records)
  },
)

// A session that ended (refresh refused, or a manual sign out) must not leave
// the previous identity's routes reachable.
watch(
  () => authStore.isAuthenticated,
  (authenticated) => {
    if (!authenticated) {
      installDynamicRoutes(router, [])
    }
  },
)

void router.isReady().then(() => {
  app.mount('#app')
})
