<script setup lang="ts">
/** Top bar: collapse toggle, breadcrumb, notifications and the user menu. */
import { computed, ref } from 'vue'
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
import { Expand, Fold, Moon, Sunny, SwitchButton, User } from '@element-plus/icons-vue'

import ChangePasswordDialog from '@/layouts/components/ChangePasswordDialog.vue'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()

const passwordDialogVisible = ref(false)

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
  appStore.clearTabs()
  await router.replace({ name: 'login' })
}

function onCommand(command: string | number | object): void {
  if (command === 'sign-out') {
    void onSignOut()
    return
  }
  if (command === 'password') {
    passwordDialogVisible.value = true
    return
  }
  if (command === 'profile') {
    void router.push({ name: 'profile' })
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

      <ElTooltip :content="appStore.theme === 'dark' ? '切换为浅色' : '切换为深色'" placement="bottom">
        <button
          type="button"
          class="header-bar__icon-button"
          :aria-label="appStore.theme === 'dark' ? '切换为浅色' : '切换为深色'"
          @click="appStore.toggleTheme()"
        >
          <ElIcon :size="17">
            <Sunny v-if="appStore.theme === 'dark'" />
            <Moon v-else />
          </ElIcon>
        </button>
      </ElTooltip>

      <ElDropdown trigger="click" @command="onCommand">
        <button type="button" class="header-bar__user">
          <ElIcon><User /></ElIcon>
          <span class="header-bar__username">{{ authStore.displayName || authStore.username }}</span>
        </button>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem command="profile">账号信息</ElDropdownItem>
            <ElDropdownItem command="password">修改密码</ElDropdownItem>
            <ElDropdownItem divided command="sign-out">
              <ElIcon><SwitchButton /></ElIcon>
              <span>退出登录</span>
            </ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>
    </div>

    <ChangePasswordDialog v-model="passwordDialogVisible" />
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

.header-bar__icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid transparent;
  border-radius: var(--vctn-radius-md);
  background: transparent;
  color: var(--vctn-text-secondary);
  cursor: pointer;
  transition:
    background-color var(--vctn-duration-fast) var(--vctn-ease),
    color var(--vctn-duration-fast) var(--vctn-ease),
    border-color var(--vctn-duration-fast) var(--vctn-ease);
}

.header-bar__icon-button:hover {
  border-color: var(--vctn-border);
  background-color: var(--vctn-bg-hover);
  color: var(--vctn-text-strong);
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
