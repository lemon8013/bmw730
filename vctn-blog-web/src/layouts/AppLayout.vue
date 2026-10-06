<script setup lang="ts">
/** Blog shell: brand, category navigation, search and the account area. */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { listCategories } from '@/api/blog'
import UserMenu from '@/components/UserMenu.vue'
import { useAsyncData } from '@/composables/use-async-data'

const route = useRoute()
const router = useRouter()

const keyword = ref('')

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

const categories = useAsyncData(() => listCategories(50))
</script>

<template>
  <div class="app-layout">
    <header class="app-layout__header">
      <div class="app-layout__header-inner">
        <RouterLink to="/" class="app-layout__brand">VCTN Blog</RouterLink>

        <nav class="app-layout__nav">
          <RouterLink :to="{ name: 'home' }" class="app-layout__nav-link">首页</RouterLink>
          <RouterLink
            v-for="category in categories.data.value?.items ?? []"
            :key="category.id"
            :to="{ name: 'category', params: { code: category.category_code } }"
            class="app-layout__nav-link"
          >
            {{ category.category_name }}
          </RouterLink>
          <RouterLink :to="{ name: 'authors' }" class="app-layout__nav-link">作者</RouterLink>
        </nav>

        <ElInput
          v-model="keyword"
          class="app-layout__search"
          placeholder="搜索文章…"
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

    <footer class="app-layout__footer">VCTN Blog · 由 VCTN 统一后端提供服务</footer>
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
  background-color: color-mix(in srgb, var(--vctn-bg-surface) 90%, transparent);
  backdrop-filter: saturate(180%) blur(10px);
  border-bottom: 1px solid var(--vctn-border-subtle);
}

.app-layout__header-inner {
  display: flex;
  align-items: center;
  gap: var(--vctn-space-4);
  max-width: 1080px;
  margin: 0 auto;
  padding: 10px var(--vctn-space-5);
}

.app-layout__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--vctn-space-2);
  color: var(--vctn-text-strong);
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.01em;
  text-decoration: none;
  white-space: nowrap;
}

.app-layout__brand::before {
  content: '';
  width: 20px;
  height: 20px;
  border-radius: var(--vctn-radius-sm);
  background-color: var(--vctn-brand-soft);
  border: 1px solid var(--vctn-border-brand);
}

.app-layout__nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--vctn-space-1);
}

.app-layout__nav-link {
  padding: 6px var(--vctn-space-3);
  border-radius: var(--vctn-radius-pill);
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition:
    background-color var(--vctn-duration-fast) var(--vctn-ease),
    color var(--vctn-duration-fast) var(--vctn-ease);
}

.app-layout__nav-link:hover {
  background-color: var(--vctn-bg-hover);
  color: var(--vctn-text-strong);
}

.app-layout__nav-link.router-link-active {
  background-color: var(--vctn-brand-soft);
  color: var(--vctn-brand);
}

.app-layout__search {
  width: 240px;
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
  padding: var(--vctn-space-6) var(--vctn-space-5) 56px;
}

.app-layout__footer {
  padding: var(--vctn-space-5);
  border-top: 1px solid var(--vctn-border-subtle);
  color: var(--vctn-text-muted);
  font-size: var(--vctn-text-xs);
  text-align: center;
}
</style>
