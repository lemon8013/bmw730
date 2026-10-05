<script setup lang="ts">
/**
 * The authenticated shell: sidebar, top bar, tabs and the page outlet.
 *
 * The shell itself holds no business logic — it renders whatever the permission
 * projection produced and delegates every decision to the router guards.
 */
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { ElScrollbar } from 'element-plus'

import HeaderBar from '@/layouts/components/HeaderBar.vue'
import SideMenu from '@/layouts/components/SideMenu.vue'
import TabsBar from '@/layouts/components/TabsBar.vue'
import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'

const appStore = useAppStore()
const permissionStore = usePermissionStore()

const hasMenu = computed(() => permissionStore.menuGroups.length > 0)
</script>

<template>
  <div class="admin-layout">
    <aside
      class="admin-layout__aside"
      :class="{ 'admin-layout__aside--collapsed': appStore.sidebarCollapsed }"
    >
      <div class="admin-layout__brand">
        <span class="admin-layout__brand-mark">V</span>
        <span v-if="!appStore.sidebarCollapsed" class="admin-layout__brand-text">
          {{ appStore.applicationName }}
        </span>
      </div>
      <ElScrollbar class="admin-layout__menu">
        <SideMenu v-if="hasMenu" />
        <p v-else class="admin-layout__menu-empty">当前账号没有任何菜单权限</p>
      </ElScrollbar>
    </aside>

    <div class="admin-layout__main">
      <HeaderBar />
      <TabsBar />
      <ElScrollbar class="admin-layout__content">
        <div class="admin-layout__content-inner">
          <RouterView v-slot="{ Component }">
            <component :is="Component" />
          </RouterView>
        </div>
      </ElScrollbar>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.admin-layout__aside {
  display: flex;
  flex-direction: column;
  width: 220px;
  overflow: hidden;
  border-right: 1px solid var(--el-border-color-lighter);
  background-color: var(--el-bg-color);
  transition: width 0.2s ease;
}

.admin-layout__aside--collapsed {
  width: 64px;
}

.admin-layout__brand {
  display: flex;
  gap: 8px;
  align-items: center;
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-weight: 600;
  white-space: nowrap;
}

.admin-layout__brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background-color: var(--el-color-primary);
  color: #fff;
  font-size: 14px;
}

.admin-layout__menu {
  flex: 1;
  min-height: 0;
}

.admin-layout__menu-empty {
  padding: 16px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.admin-layout__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.admin-layout__content {
  flex: 1;
  min-height: 0;
  background-color: var(--el-fill-color-blank);
}

.admin-layout__content-inner {
  padding: 16px;
}

@media (max-width: 1024px) {
  .admin-layout__aside {
    width: 64px;
  }

  .admin-layout__brand-text {
    display: none;
  }
}
</style>
