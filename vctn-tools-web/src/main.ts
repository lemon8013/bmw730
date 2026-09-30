import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import { createApp } from 'vue'

import 'element-plus/dist/index.css'
import '@/styles/index.css'

import App from '@/App.vue'
import { createAppRouter } from '@/router'
import { toolDefinitions } from '@/tools/definitions'
import { toolRegistry } from '@/tools/registry'

// Phase 0 bootstrap: register the (currently empty) built-in tool catalogue.
toolRegistry.registerMany(toolDefinitions)

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(ElementPlus)

app.mount('#app')
