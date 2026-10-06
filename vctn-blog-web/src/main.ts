import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import { createApp } from 'vue'

import 'element-plus/dist/index.css'
import '@/styles/tokens.css'
import '@/styles/index.css'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(ElementPlus)

// Reading the blog needs no session, so restoring one is best effort: it must
// never delay the first paint, and a failure simply leaves the visitor a reader.
const auth = useAuthStore()
auth.bindSessionExpiry()
void auth.restore()

app.mount('#app')
