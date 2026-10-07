/**
 * Application chrome state.
 *
 * The console has no dark theme: it is a wall-board application that stays on
 * one palette, so unlike the management platform there is nothing to switch.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { apiBaseUrl } from '@/api/endpoint'
import { APP_TITLE } from '@/router/route-table'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const applicationName = ref(APP_TITLE)
  const apiPrefix = ref(apiBaseUrl)

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarCollapsed, applicationName, apiPrefix, toggleSidebar }
})
