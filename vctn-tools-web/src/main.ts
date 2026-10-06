import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import { createApp } from 'vue'

import 'element-plus/dist/index.css'
import '@/styles/index.css'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { toolDefinitions } from '@/tools/definitions'
import { toolRegistry } from '@/tools/registry'
import { registerBuiltinExecutors, toolRuntime } from '@/tools/runtime'

// Register the built-in tool components (build time, never from remote input).
toolRegistry.registerMany(toolDefinitions)
// One executor per frozen execution mode: FRONTEND / BACKEND / ASYNC.
registerBuiltinExecutors(toolRuntime.registerExecutor.bind(toolRuntime))

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(ElementPlus)

// The portal is anonymous by default, so restoring a session is best effort:
// it must never delay the first paint, and a failure simply leaves the visitor
// signed out.
const auth = useAuthStore()
auth.bindSessionExpiry()
void auth.restore()

app.mount('#app')
