<script setup lang="ts">
/**
 * Open page tabs, mirroring the router.
 *
 * Right-clicking a tab opens a context menu with 关闭当前 / 关闭左侧所有 /
 * 关闭右侧所有 / 全部关闭, the behaviour every multi-tab console is expected to
 * have. The menu is drawn by this component rather than by a UI-library
 * primitive because Element Plus does not ship a context menu.
 */
import { computed, onBeforeUnmount, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElIcon, ElTag } from 'element-plus'
import { Close } from '@element-plus/icons-vue'

import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const activePath = computed(() => route.path)

/** Context menu state: where it is drawn and which tab it acts on. */
const menu = reactive<{ visible: boolean; x: number; y: number; path: string }>({
  visible: false,
  x: 0,
  y: 0,
  path: '',
})

const menuIndex = computed(() => appStore.tabs.findIndex((tab) => tab.path === menu.path))
const canCloseLeft = computed(() => menuIndex.value > 0)
const canCloseRight = computed(
  () => menuIndex.value !== -1 && menuIndex.value < appStore.tabs.length - 1,
)
const canCloseAll = computed(() => appStore.tabs.length > 0)

watch(
  () => route.fullPath,
  () => {
    const title = route.meta.title
    const name = typeof route.name === 'string' ? route.name : ''
    if (typeof title !== 'string' || name === '') {
      return
    }
    if (name === 'login' || name === 'change-password' || name === 'profile') {
      return
    }
    appStore.openTab({ path: route.path, title, name })
  },
  { immediate: true },
)

/** Keep the menu inside the viewport. */
const MENU_WIDTH = 160
const MENU_HEIGHT = 168

function openMenu(event: MouseEvent, path: string): void {
  event.preventDefault()
  const maxX = window.innerWidth - MENU_WIDTH - 8
  const maxY = window.innerHeight - MENU_HEIGHT - 8
  menu.path = path
  menu.x = Math.max(4, Math.min(event.clientX, maxX))
  menu.y = Math.max(4, Math.min(event.clientY, maxY))
  menu.visible = true
}

function closeMenu(): void {
  menu.visible = false
}

function onSelect(path: string): void {
  if (path !== activePath.value) {
    void router.push(path)
  }
}

function onClose(path: string): void {
  const next = appStore.closeTab(path)
  if (path === activePath.value) {
    void router.push(next ?? appStore.sidebarDefaultPath())
  }
}

function onCloseOthers(): void {
  appStore.keepOnly(activePath.value)
}

/** Close the tab the menu belongs to. */
function menuCloseCurrent(): void {
  const target = menu.path
  closeMenu()
  onClose(target)
}

/**
 * Close every tab left of the target.
 *
 * The open page is only moved when it was among the removed tabs, so closing
 * neighbours never yanks the operator away from the page they are reading.
 */
function menuCloseLeft(): void {
  const target = menu.path
  closeMenu()
  const active = activePath.value
  const removed = isBefore(active, target)
  appStore.closeLeft(target)
  if (removed) {
    void router.push(target)
  }
}

/** Close every tab right of the target. */
function menuCloseRight(): void {
  const target = menu.path
  closeMenu()
  const active = activePath.value
  const removed = isBefore(target, active)
  appStore.closeRight(target)
  if (removed) {
    void router.push(target)
  }
}

/** Whether `left` sits strictly before `right` among the open tabs. */
function isBefore(left: string, right: string): boolean {
  const leftIndex = appStore.tabs.findIndex((tab) => tab.path === left)
  const rightIndex = appStore.tabs.findIndex((tab) => tab.path === right)
  return leftIndex !== -1 && rightIndex !== -1 && leftIndex < rightIndex
}

/** Close every tab, then land on the default page. */
function menuCloseAll(): void {
  closeMenu()
  appStore.clearTabs()
  void router.push(appStore.sidebarDefaultPath())
}

// A click, a scroll or a resize anywhere dismisses the menu.
if (typeof window !== 'undefined') {
  window.addEventListener('click', closeMenu)
  window.addEventListener('scroll', closeMenu, true)
  window.addEventListener('resize', closeMenu)
  onBeforeUnmount(() => {
    window.removeEventListener('click', closeMenu)
    window.removeEventListener('scroll', closeMenu, true)
    window.removeEventListener('resize', closeMenu)
  })
}
</script>

<template>
  <div class="tabs-bar">
    <div class="tabs-bar__list">
      <ElTag
        v-for="tab in appStore.tabs"
        :key="tab.path"
        :type="tab.path === activePath ? 'primary' : 'info'"
        :effect="tab.path === activePath ? 'dark' : 'plain'"
        size="default"
        class="tabs-bar__tab"
        @click="onSelect(tab.path)"
        @contextmenu="openMenu($event, tab.path)"
      >
        {{ tab.title }}
        <ElIcon class="tabs-bar__close" @click.stop="onClose(tab.path)">
          <Close />
        </ElIcon>
      </ElTag>
      <span v-if="appStore.tabs.length === 0" class="tabs-bar__empty">尚未打开任何页面</span>
    </div>
    <ElTag v-if="appStore.tabs.length > 1" size="small" effect="plain" @click="onCloseOthers">
      仅保留当前
    </ElTag>

    <ul
      v-if="menu.visible"
      class="tabs-bar__menu"
      :style="{ left: `${menu.x}px`, top: `${menu.y}px` }"
      @click.stop
    >
      <li class="tabs-bar__menu-item" @click="menuCloseCurrent">关闭当前</li>
      <li
        class="tabs-bar__menu-item"
        :class="{ 'tabs-bar__menu-item--disabled': !canCloseLeft }"
        @click="canCloseLeft && menuCloseLeft()"
      >
        关闭左侧所有
      </li>
      <li
        class="tabs-bar__menu-item"
        :class="{ 'tabs-bar__menu-item--disabled': !canCloseRight }"
        @click="canCloseRight && menuCloseRight()"
      >
        关闭右侧所有
      </li>
      <li
        class="tabs-bar__menu-item tabs-bar__menu-item--divided"
        :class="{ 'tabs-bar__menu-item--disabled': !canCloseAll }"
        @click="canCloseAll && menuCloseAll()"
      >
        全部关闭
      </li>
    </ul>
  </div>
</template>

<style scoped>
.tabs-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px 0;
}

.tabs-bar__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tabs-bar__tab {
  cursor: pointer;
  user-select: none;
}

.tabs-bar__close {
  margin-left: 4px;
}

.tabs-bar__empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.tabs-bar__menu {
  position: fixed;
  z-index: 3000;
  min-width: 160px;
  margin: 0;
  padding: 4px 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 4px;
  background-color: var(--el-bg-color-overlay);
  box-shadow: var(--el-box-shadow-light);
  list-style: none;
}

.tabs-bar__menu-item {
  padding: 7px 16px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.tabs-bar__menu-item:hover {
  background-color: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.tabs-bar__menu-item--divided {
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 4px;
  padding-top: 8px;
}

.tabs-bar__menu-item--disabled {
  color: var(--el-text-color-placeholder);
  cursor: not-allowed;
  pointer-events: none;
}
</style>
