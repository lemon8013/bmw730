<script setup lang="ts">
/**
 * Sidebar menu rendered from the backend menu tree.
 *
 * Nothing here is hard coded: the groups and the pages come from the permission
 * store, which projects the menu nodes the backend returned for this session.
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElIcon, ElMenu, ElMenuItem, ElSubMenu } from 'element-plus'
import * as ElementPlusIcons from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'
import { usePermissionStore } from '@/stores/permission'

const props = defineProps<{
  /** Viewport-driven or user-driven collapse; defaults to the app store. */
  collapsed?: boolean
}>()

const route = useRoute()
const appStore = useAppStore()
const permissionStore = usePermissionStore()

const groups = computed(() => permissionStore.menuGroups)
const isCollapsed = computed(() => props.collapsed ?? appStore.sidebarCollapsed)

/** Resolve an Element Plus icon by name, falling back to a neutral one. */
function resolveIcon(name: string): unknown {
  const registry = ElementPlusIcons as unknown as Record<string, unknown>
  return registry[name] ?? registry.Menu
}

/** A single-page group is rendered as a flat item, not a submenu. */
function isSinglePage(index: number): boolean {
  const group = groups.value[index]
  return group !== undefined && group.pages.length === 1 && group.pages[0] !== undefined
}
</script>

<template>
  <ElMenu
    :default-active="route.path"
    :collapse="isCollapsed"
    :collapse-transition="false"
    class="side-menu"
    router
  >
    <template v-for="(group, index) in groups" :key="group.key">
      <ElMenuItem
        v-if="isSinglePage(index) && group.pages[0]"
        :index="group.pages[0].page.path"
        class="side-menu__item"
      >
        <!-- An ElMenuItem renders its default slot; the `title` slot is only
             used for the collapsed tooltip, so the label goes here. -->
        <ElIcon><component :is="resolveIcon(group.pages[0].icon)" /></ElIcon>
        <span class="side-menu__label">{{ group.pages[0].title }}</span>
      </ElMenuItem>

      <ElSubMenu v-else :index="group.key" class="side-menu__group">
        <template #title>
          <ElIcon><component :is="resolveIcon(group.icon)" /></ElIcon>
          <span>{{ group.title }}</span>
        </template>
        <ElMenuItem
          v-for="entry in group.pages"
          :key="entry.page.path"
          :index="entry.page.path"
          class="side-menu__item"
        >
          <ElIcon><component :is="resolveIcon(entry.icon)" /></ElIcon>
          <span class="side-menu__label">{{ entry.title }}</span>
        </ElMenuItem>
      </ElSubMenu>
    </template>
  </ElMenu>
</template>

<style scoped>
.side-menu {
  height: 100%;
  border-right: none;
  background-color: transparent;

  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--vctn-text-regular);
  --el-menu-active-color: var(--vctn-brand);
  --el-menu-hover-bg-color: var(--vctn-bg-hover);
  --el-menu-base-level-padding: 12px;
  --el-menu-level-padding: 12px;
  --el-menu-item-height: 40px;
  --el-menu-sub-item-height: 40px;
}

.side-menu:not(.el-menu--collapse) {
  width: 100%;
}

.side-menu :deep(.el-sub-menu__title),
.side-menu :deep(.el-menu-item) {
  color: var(--vctn-text-regular);
}

.side-menu :deep(.el-menu-item.is-active) {
  background-color: var(--vctn-brand-soft);
  color: var(--vctn-brand);
  font-weight: 500;
}

.side-menu :deep(.el-sub-menu__title:hover),
.side-menu :deep(.el-menu-item:hover) {
  background-color: var(--vctn-bg-hover);
  color: var(--vctn-text-strong);
}

.side-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 3px;
  height: 18px;
  border-radius: 0 var(--vctn-radius-pill) var(--vctn-radius-pill) 0;
  background-color: var(--vctn-brand);
  transform: translateY(-50%);
}

.side-menu :deep(.el-sub-menu .el-menu) {
  background-color: transparent;
}

.side-menu :deep(.el-menu-item) {
  position: relative;
}

.side-menu__label {
  margin-left: 4px;
}
</style>
