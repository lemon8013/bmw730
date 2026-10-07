/**
 * The single place that answers "may the UI show this?".
 *
 * The backend remains the only authority: this store mirrors the permission
 * codes the backend granted for the current session and never grants anything
 * on its own. It drives the dynamic menu, the router records and the write
 * buttons.
 *
 * What makes it different from the management platform's copy is the menu
 * projection: the backend returns one tree for the whole administrator, so the
 * console keeps only its own branch and drops the rest.
 */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

import { firstAllowedPath, projectMenu, type MenuGroup } from '@/router/route-builder'
import type { MenuNode } from '@/types/auth'

export const usePermissionStore = defineStore('permission', () => {
  const codes = ref<ReadonlySet<string>>(new Set())
  const menus = shallowRef<MenuNode[]>([])
  const isSuperAdmin = ref(false)
  const loaded = ref(false)
  const unwiredCodes = ref<string[]>([])
  const routeRecords = shallowRef<RouteRecordRaw[]>([])

  const project = computed(() => projectMenu(menus.value, (code) => codes.value.has(code)))

  const menuGroups = computed<MenuGroup[]>(() => project.value.groups)

  const landingPath = computed(() => firstAllowedPath(project.value))

  /** Replace the whole permission state for a new session. */
  function applyPermissions(payload: {
    permissions: readonly string[]
    menus: readonly MenuNode[]
    is_super_admin: boolean
  }): void {
    codes.value = new Set(payload.permissions)
    menus.value = [...payload.menus]
    isSuperAdmin.value = payload.is_super_admin
    const projected = projectMenu(menus.value, (code) => codes.value.has(code))
    unwiredCodes.value = projected.unwired
    routeRecords.value = projected.routes
    loaded.value = true
  }

  /** Drop every permission for the current session. */
  function reset(): void {
    codes.value = new Set()
    menus.value = []
    isSuperAdmin.value = false
    loaded.value = false
    unwiredCodes.value = []
    routeRecords.value = []
  }

  /** Whether the caller holds a permission code. */
  function has(permissionCode: string): boolean {
    if (isSuperAdmin.value) {
      return true
    }
    return codes.value.has(permissionCode)
  }

  /** Whether the caller holds at least one of the codes. */
  function any(permissionCodes: readonly string[]): boolean {
    if (permissionCodes.length === 0) {
      return true
    }
    if (isSuperAdmin.value) {
      return true
    }
    return permissionCodes.some((code) => codes.value.has(code))
  }

  return {
    codes,
    menus,
    isSuperAdmin,
    loaded,
    unwiredCodes,
    routeRecords,
    menuGroups,
    landingPath,
    applyPermissions,
    reset,
    has,
    any,
  }
})
