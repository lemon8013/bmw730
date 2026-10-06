<script setup lang="ts">
/** Portal shell: brand, primary navigation and the global search box. */
import { computed, ref, watch } from 'vue'
import { HomeFilled } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

import UserMenu from '@/components/UserMenu.vue'
import { useAppStore } from '@/stores/app'

const store = useAppStore()
const route = useRoute()
const router = useRouter()

const keyword = ref('')

// Keep the box in sync when the user lands on /search?keyword=… directly.
watch(
  () => route.query.keyword,
  (value) => {
    keyword.value = typeof value === 'string' ? value : ''
  },
  { immediate: true },
)

function submitSearch(): void {
  const trimmed = keyword.value.trim()
  if (trimmed === '') {
    return
  }
  void router.push({ name: 'search', query: { keyword: trimmed } })
}

const navigation = [
  { name: 'home', label: '首页' },
  { name: 'popular', label: '热门' },
  { name: 'recent', label: '最近使用' },
] as const

/** Any page except `/` gets an explicit way back to the catalogue. */
const canGoHome = computed(() => route.name !== 'home')

function goHome(): void {
  void router.push({ name: 'home' })
}
</script>

<template>
  <div class="app-layout">
    <header class="app-layout__header">
      <div class="app-layout__header-inner">
        <RouterLink to="/" class="app-layout__brand" title="返回首页">
          <ElIcon :size="18" class="app-layout__brand-icon"><HomeFilled /></ElIcon>
          <span>{{ store.applicationName }}</span>
        </RouterLink>

        <ElButton
          v-if="canGoHome"
          class="app-layout__home-button"
          size="small"
          text
          bg
          @click="goHome"
        >
          返回首页
        </ElButton>

        <nav class="app-layout__nav">
          <RouterLink
            v-for="item in navigation"
            :key="item.name"
            :to="{ name: item.name }"
            class="app-layout__nav-link"
            :class="{ 'app-layout__nav-link--active': route.name === item.name }"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <ElInput
          v-model="keyword"
          class="app-layout__search"
          placeholder="搜索工具…"
          clearable
          @keyup.enter="submitSearch"
        >
          <template #append>
            <ElButton @click="submitSearch">搜索</ElButton>
          </template>
        </ElInput>

        <UserMenu class="app-layout__user" />
      </div>
    </header>

    <main class="app-layout__main">
      <RouterView />
    </main>

    <footer class="app-layout__footer">
      VCTN Tools · 输入内容默认只在浏览器内处理，不会因埋点自动上传
    </footer>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.app-layout__header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.app-layout__header-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  max-width: 1080px;
  margin: 0 auto;
  padding: 12px 20px;
}

.app-layout__brand {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
  font-weight: 700;
  color: var(--el-color-primary);
  text-decoration: none;
  white-space: nowrap;
}

.app-layout__brand:hover {
  opacity: 0.85;
}

.app-layout__home-button {
  flex: none;
}

.app-layout__nav {
  display: flex;
  gap: 4px;
}

.app-layout__nav-link {
  padding: 6px 12px;
  border-radius: 6px;
  color: var(--el-text-color-regular);
  text-decoration: none;
}

.app-layout__nav-link:hover {
  background: var(--el-fill-color-light);
}

.app-layout__nav-link--active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
}

.app-layout__search {
  width: 280px;
  margin-left: auto;
}

.app-layout__user {
  flex: none;
}

.app-layout__main {
  flex: 1;
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  padding: 20px;
}

.app-layout__footer {
  padding: 16px 20px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-align: center;
}
</style>
