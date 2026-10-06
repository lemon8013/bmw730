<script setup lang="ts">
/**
 * The authenticated shell: sidebar, top bar, tabs and the page outlet.
 *
 * The shell itself holds no business logic — it renders whatever the permission
 * projection produced and delegates every decision to the router guards.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import { ElScrollbar } from 'element-plus'

import HeaderBar from '@/layouts/components/HeaderBar.vue'
import SideMenu from '@/layouts/components/SideMenu.vue'
import TabsBar from '@/layouts/components/TabsBar.vue'
import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'

const NARROW_QUERY = '(max-width: 1024px)'

const appStore = useAppStore()
const permissionStore = usePermissionStore()

const hasMenu = computed(() => permissionStore.menuGroups.length > 0)

/** Viewport-driven collapse: the menu folds instead of being squeezed. */
const isNarrowViewport = ref(window.matchMedia(NARROW_QUERY).matches)
let narrowQuery: MediaQueryList | null = null

function syncNarrow(event: MediaQueryListEvent): void {
  isNarrowViewport.value = event.matches
}

onMounted(() => {
  narrowQuery = window.matchMedia(NARROW_QUERY)
  narrowQuery.addEventListener('change', syncNarrow)
})

onBeforeUnmount(() => {
  narrowQuery?.removeEventListener('change', syncNarrow)
})

const sidebarCollapsed = computed(
  () => appStore.sidebarCollapsed || isNarrowViewport.value,
)
</script>

<template>
  <div class="admin-layout">
    <aside
      class="admin-layout__aside"
      :class="{ 'admin-layout__aside--collapsed': sidebarCollapsed }"
    >
      <div class="admin-layout__brand">
        <span class="admin-layout__brand-mark">V</span>
        <span v-if="!sidebarCollapsed" class="admin-layout__brand-text">
          <span class="admin-layout__brand-name">{{ appStore.applicationName }}</span>
          <span class="admin-layout__brand-version">v{{ appStore.version }}</span>
        </span>
      </div>
      <ElScrollbar class="admin-layout__menu">
        <SideMenu v-if="hasMenu" :collapsed="sidebarCollapsed" />
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
  width: var(--vctn-sidebar-width);
  overflow: hidden;
  border-right: 1px solid var(--vctn-border-subtle);
  background-color: var(--vctn-bg-surface);
  transition: width var(--vctn-duration-base) var(--vctn-ease);
}

.admin-layout__aside--collapsed {
  width: var(--vctn-sidebar-width-collapsed);
}

.admin-layout__brand {
  display: flex;
  gap: var(--vctn-space-2);
  align-items: center;
  height: var(--vctn-header-height);
  padding: 0 var(--vctn-space-4);
  border-bottom: 1px solid var(--vctn-border-subtle);
  white-space: nowrap;
}

.admin-layout__brand-mark {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--vctn-radius-sm);
  background-color: var(--vctn-brand);
  color: var(--vctn-text-inverse);
  font-size: var(--vctn-text-base);
  font-weight: 500;
  letter-spacing: 0.02em;
}

.admin-layout__brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}

.admin-layout__brand-name {
  overflow: hidden;
  color: var(--vctn-text-strong);
  font-size: var(--vctn-text-sm);
  font-weight: 500;
  text-overflow: ellipsis;
}

.admin-layout__brand-version {
  color: var(--vctn-text-muted);
  font-family: var(--vctn-font-mono);
  font-size: 11px;
}

.admin-layout__menu {
  flex: 1;
  min-height: 0;
  padding-top: var(--vctn-space-2);
}

.admin-layout__menu-empty {
  padding: var(--vctn-space-4);
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-xs);
  line-height: 1.6;
}

.admin-layout__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  background-color: var(--vctn-bg-page);
}

.admin-layout__content {
  flex: 1;
  min-height: 0;
  background-color: var(--vctn-bg-page);
}

.admin-layout__content-inner {
  padding: var(--vctn-space-4);
}

@media (min-width: 1600px) {
  .admin-layout__content-inner {
    max-width: var(--vctn-content-max);
    margin: 0 auto;
  }
}
</style>
