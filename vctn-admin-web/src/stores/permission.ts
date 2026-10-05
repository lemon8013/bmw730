/**
 * The single place that answers "may the UI show this?".
 *
 * The backend remains the only authority: this store mirrors the permission
 * codes the backend granted for the current session and never grants anything
 * on its own. It drives the dynamic menu, the router records, the button
 * directive and the field policy.
 */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

import { listAllPermissionResources } from '@/api/permissions'
import { firstAllowedPath, projectMenu, type MenuGroup } from '@/router/route-builder'
import type { MenuNode } from '@/types/auth'
import type { FieldPermissionOutput, PermissionResource } from '@/types/system'
import { FIELD_MODE, type FieldMode } from '@/types/enums'

/**
 * Fields that are never rendered, whatever the backend says.
 *
 * The backend already enforces this, but the frontend refuses to relax it even
 * if a policy is misconfigured: password material and MFA secrets have no
 * legitimate place in an administration screen.
 */
const NEVER_VISIBLE_FIELDS: readonly string[] = [
  'password',
  'password_hash',
  'passwordhash',
  'mfa_secret',
  'mfa_secret_encrypted',
  'access_token',
  'refresh_token',
  'token',
  'secret',
  'api_key',
  'apikey',
  'cookie',
  'authorization',
]

function normaliseField(field: string): string {
  return field.trim().toLowerCase()
}

/** Whether a field name is on the unconditional deny list. */
export function isNeverVisibleField(field: string): boolean {
  const normalised = normaliseField(field)
  if (NEVER_VISIBLE_FIELDS.includes(normalised)) {
    return true
  }
  return normalised.endsWith('_secret') || normalised.endsWith('_token')
}

/** Merge a backend policy map with the local deny list. */
export function mergeFieldPolicy(
  policy: Readonly<Record<string, FieldMode>>,
  fields: readonly string[],
): Record<string, FieldMode> {
  const merged: Record<string, FieldMode> = {}
  for (const field of fields) {
    if (isNeverVisibleField(field)) {
      merged[field] = 'HIDDEN'
      continue
    }
    merged[field] = policy[field] ?? 'VISIBLE'
  }
  return merged
}

export const usePermissionStore = defineStore('permission', () => {
  const codes = ref<ReadonlySet<string>>(new Set())
  const menus = shallowRef<MenuNode[]>([])
  const isSuperAdmin = ref(false)
  const loaded = ref(false)
  const unwiredCodes = ref<string[]>([])
  const routeRecords = shallowRef<RouteRecordRaw[]>([])

  /** Field policy per permission code, as declared by the backend. */
  const fieldPolicy = ref<Record<string, Record<string, FieldMode>>>({})

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
    fieldPolicy.value = {}
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

  /** Whether the caller holds every code. */
  function all(permissionCodes: readonly string[]): boolean {
    if (permissionCodes.length === 0) {
      return true
    }
    if (isSuperAdmin.value) {
      return true
    }
    return permissionCodes.every((code) => codes.value.has(code))
  }

  /** The effective field policy for one permission code. */
  function fieldModes(permissionCode: string): Record<string, FieldMode> {
    return fieldPolicy.value[permissionCode] ?? {}
  }

  /**
   * Load the field policies declared on the permission resources.
   *
   * Field policies are attached to permission resources, so reading them needs
   * `PERMISSION_VIEW`. Without it the local deny list still applies, which is
   * strictly stricter and therefore safe.
   */
  async function loadFieldPolicies(): Promise<void> {
    if (!has('PERMISSION_VIEW')) {
      return
    }
    try {
      const resources: PermissionResource[] = await listAllPermissionResources()
      const next: Record<string, Record<string, FieldMode>> = {}
      for (const resource of resources) {
        const declared: FieldPermissionOutput[] = resource.field_permissions ?? []
        if (declared.length === 0) {
          continue
        }
        const modes: Record<string, FieldMode> = {}
        for (const entry of declared) {
          const mode = entry.field_mode as FieldMode
          modes[entry.field_code] = FIELD_MODE.includes(mode) ? mode : 'HIDDEN'
        }
        next[resource.permission_code] = modes
      }
      fieldPolicy.value = next
    } catch {
      // A missing or refused resource listing must not break the session.
      fieldPolicy.value = {}
    }
  }

  return {
    codes,
    menus,
    isSuperAdmin,
    loaded,
    unwiredCodes,
    routeRecords,
    fieldPolicy,
    menuGroups,
    landingPath,
    applyPermissions,
    reset,
    has,
    any,
    all,
    fieldModes,
    loadFieldPolicies,
  }
})
