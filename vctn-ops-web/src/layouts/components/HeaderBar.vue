<script setup lang="ts">
/** Top bar: collapse toggle, breadcrumb, the API prefix and the user menu. */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ElBreadcrumb,
  ElBreadcrumbItem,
  ElButton,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElIcon,
  ElTooltip,
} from 'element-plus'
import { Expand, Fold, SwitchButton, User } from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

/** Breadcrumb entries derived from the matched route list. */
const breadcrumb = computed(() => {
  const titles: string[] = []
  for (const matched of route.matched) {
    const title = matched.meta.title
    if (typeof title === 'string' && title.length > 0) {
      titles.push(title)
    }
  }
  return titles
})

async function onSignOut(): Promise<void> {
  await authStore.signOut()
  await router.replace({ name: 'login' })
}

function onCommand(command: string | number | object): void {
  if (command === 'sign-out') {
    void onSignOut()
  }
}
</script>

<template>
  <header class="header-bar">
    <div class="header-bar__left">
      <ElButton text class="header-bar__toggle" @click="appStore.toggleSidebar()">
        <ElIcon :size="18">
          <Fold v-if="!appStore.sidebarCollapsed" />
          <Expand v-else />
        </ElIcon>
      </ElButton>

      <ElBreadcrumb separator="/" class="header-bar__breadcrumb">
        <ElBreadcrumbItem v-for="(title, index) in breadcrumb" :key="`${index}-${title}`">
          {{ title }}
        </ElBreadcrumbItem>
      </ElBreadcrumb>
    </div>

    <div class="header-bar__right">
      <ElTooltip content="后端 API 前缀" placement="bottom">
        <span class="header-bar__api">{{ appStore.apiPrefix }}</span>
      </ElTooltip>

      <ElDropdown trigger="click" @command="onCommand">
        <button type="button" class="header-bar__user">
          <ElIcon><User /></ElIcon>
          <span class="header-bar__username">{{ authStore.displayName || authStore.username }}</span>
        </button>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem divided command="sign-out">
              <ElIcon><SwitchButton /></ElIcon>
              <span>退出登录</span>
            </ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>
    </div>
  </header>
</template>

<style scoped>
.header-bar {
  display: flex;
  gap: var(--vctn-space-3);
  align-items: center;
  justify-content: space-between;
  height: var(--vctn-header-height);
  padding: 0 var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
  background-color: var(--vctn-bg-surface);
}

.header-bar__left,
.header-bar__right {
  display: flex;
  gap: var(--vctn-space-2);
  align-items: center;
  min-width: 0;
}

.header-bar__toggle {
  padding: var(--vctn-space-1);
  border-radius: var(--vctn-radius-sm);
}

.header-bar__breadcrumb {
  overflow: hidden;
  white-space: nowrap;
}

.header-bar__api {
  padding: 3px 8px;
  border: 1px solid var(--vctn-border-subtle);
  border-radius: var(--vctn-radius-pill);
  background-color: var(--vctn-bg-inset);
  color: var(--vctn-text-secondary);
  font-family: var(--vctn-font-mono);
  font-size: var(--vctn-text-xs);
}

.header-bar__user {
  display: flex;
  gap: var(--vctn-space-2);
  align-items: center;
  height: 32px;
  padding: 0 var(--vctn-space-2);
  border: 1px solid transparent;
  border-radius: var(--vctn-radius-md);
  background: transparent;
  color: var(--vctn-text-regular);
  cursor: pointer;
  font-size: var(--vctn-text-sm);
  transition:
    background-color var(--vctn-duration-fast) var(--vctn-ease),
    border-color var(--vctn-duration-fast) var(--vctn-ease);
}

.header-bar__user:hover {
  border-color: var(--vctn-border);
  background-color: var(--vctn-bg-hover);
}

.header-bar__username {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
