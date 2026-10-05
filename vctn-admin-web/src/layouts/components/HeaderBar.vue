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
import { Expand, Fold, SwitchButton, User } from '@element-plus/icons-vue'

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
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background-color: var(--el-bg-color);
}

.header-bar__left,
.header-bar__right {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.header-bar__toggle {
  padding: 4px;
}

.header-bar__breadcrumb {
  overflow: hidden;
  white-space: nowrap;
}

.header-bar__api {
  color: var(--el-text-color-secondary);
  font-family: monospace;
  font-size: 12px;
}

.header-bar__user {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 6px 10px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--el-text-color-primary);
  cursor: pointer;
  font-size: 14px;
}

.header-bar__user:hover {
  background-color: var(--el-fill-color-light);
}

.header-bar__username {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
