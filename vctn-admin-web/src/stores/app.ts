/** Shell state: sidebar, breadcrumb and the open page tabs. */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiBaseUrl, appVersion } from '@/api/endpoint'

/** One open page tab. */
export interface PageTab {
  path: string
  title: string
  name: string
}

const SIDEBAR_KEY = 'vctn.admin.sidebar_collapsed'
const TABS_KEY = 'vctn.admin.page_tabs'
const THEME_KEY = 'vctn.admin.theme'

/** The console supports a light and a dark palette. */
export type ThemeMode = 'light' | 'dark'

function readPreference(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Ignored on purpose: layout preferences are cosmetic.
  }
}

/**
 * Reflect the palette on <html>.
 *
 * Guarded because the store is also imported outside the browser, and kept in
 * one place so no component has to know how theming is implemented.
 */
function applyTheme(mode: ThemeMode): void {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.classList.toggle('dark', mode === 'dark')
  document.documentElement.style.colorScheme = mode
}

export const useAppStore = defineStore('app', () => {
  const applicationName = ref('VCTN 管理平台')
  const sidebarCollapsed = ref(readPreference(SIDEBAR_KEY) === '1')
  const tabs = ref<PageTab[]>([])
  const theme = ref<ThemeMode>(readPreference(THEME_KEY) === 'dark' ? 'dark' : 'light')

  const apiPrefix = computed(() => apiBaseUrl)
  const version = computed(() => appVersion)

  // Paint the stored palette before anything mounts, so a reload never flashes.
  applyTheme(theme.value)

  /** Switch between the light and the dark palette and remember the choice. */
  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    writePreference(THEME_KEY, theme.value)
    applyTheme(theme.value)
  }

  /** Collapse or expand the sidebar and remember the choice. */
  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
    writePreference(SIDEBAR_KEY, sidebarCollapsed.value ? '1' : '0')
  }

  /** Force one sidebar state. */
  function setSidebarCollapsed(collapsed: boolean): void {
    sidebarCollapsed.value = collapsed
    writePreference(SIDEBAR_KEY, collapsed ? '1' : '0')
  }

  /** Remember an opened page as a tab. */
  function openTab(tab: PageTab): void {
    if (tabs.value.some((item) => item.path === tab.path)) {
      return
    }
    tabs.value = [...tabs.value, tab]
    writePreference(TABS_KEY, JSON.stringify(tabs.value))
  }

  /** Close one tab; returns the path to navigate to, or `null`. */
  function closeTab(path: string): string | null {
    const index = tabs.value.findIndex((item) => item.path === path)
    if (index === -1) {
      return null
    }
    const next = tabs.value.filter((item) => item.path !== path)
    tabs.value = next
    writePreference(TABS_KEY, JSON.stringify(next))
    if (next.length === 0) {
      return null
    }
    return next[Math.min(index, next.length - 1)].path
  }

  /** Keep only one tab open. */
  function keepOnly(path: string): void {
    tabs.value = tabs.value.filter((item) => item.path === path)
    writePreference(TABS_KEY, JSON.stringify(tabs.value))
  }

  /**
   * Close every tab to the left of `path`.
   *
   * Returns the path to navigate to when the active tab was removed, or `null`
   * when the caller should stay where it is.
   */
  function closeLeft(path: string): string | null {
    const index = tabs.value.findIndex((item) => item.path === path)
    if (index <= 0) {
      return null
    }
    tabs.value = tabs.value.filter((_, position) => position >= index)
    writePreference(TABS_KEY, JSON.stringify(tabs.value))
    return null
  }

  /** Close every tab to the right of `path`. */
  function closeRight(path: string): string | null {
    const index = tabs.value.findIndex((item) => item.path === path)
    if (index === -1 || index === tabs.value.length - 1) {
      return null
    }
    tabs.value = tabs.value.filter((_, position) => position <= index)
    writePreference(TABS_KEY, JSON.stringify(tabs.value))
    return null
  }

  /** Forget every tab, used on sign out. */
  function clearTabs(): void {
    tabs.value = []
    writePreference(TABS_KEY, '[]')
  }

  /**
   * A safe path to fall back to when the last tab is closed.
   *
   * Deliberately a fixed route rather than a permission derived one: the caller
   * is closing a tab because it is going away, and the router guard will bounce
   * to `/403` if this identity may not open it.
   */
  function sidebarDefaultPath(): string {
    return '/'
  }

  return {
    applicationName,
    sidebarCollapsed,
    tabs,
    theme,
    apiPrefix,
    version,
    toggleTheme,
    toggleSidebar,
    setSidebarCollapsed,
    openTab,
    closeTab,
    keepOnly,
    closeLeft,
    closeRight,
    clearTabs,
    sidebarDefaultPath,
  }
})
