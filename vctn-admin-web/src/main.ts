import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import { createApp } from 'vue'

import 'element-plus/dist/index.css'
import '@/styles/index.css'

import App from '@/App.vue'
import { createAppRouter } from '@/router'

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(ElementPlus)

app.mount('#app')
