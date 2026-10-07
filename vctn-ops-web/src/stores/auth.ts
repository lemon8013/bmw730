/**
 * Session state: who is signed in, and whether the session is still usable.
 *
 * The store owns the login/logout lifecycle. Tokens live in
 * `@/api/credentials`; this store never reads them.
 *
 * The console authenticates against the same administrator directory as the
 * management platform (`/admin/auth/*`), so an operator reuses one identity —
 * while the `vctn.ops.` sessionStorage prefix keeps the two sites' sessions
 * strictly separate.
 */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import {
  fetchCurrentUser,
  fetchPermissions,
  login as loginRequest,
  logout as logoutRequest,
} from '@/api/auth'
import { clearCredentials, readCredentials, writeCredentials } from '@/api/credentials'
import { endSession, onSessionExpired } from '@/api/refresh'
import { usePermissionStore } from '@/stores/permission'
import type { AdminUserBrief, LoginRequest } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = shallowRef<AdminUserBrief | null>(null)
  const mustChangePassword = ref(false)
  const initialising = ref(false)
  const ready = ref(false)
  const sessionEnded = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const displayName = computed(() => user.value?.display_name ?? '')
  const username = computed(() => user.value?.username ?? '')
  const isSuperAdmin = computed(() => user.value?.is_super_admin === true)

  /** Load identity plus permissions for the current credentials. */
  async function loadSession(): Promise<void> {
    const permissionStore = usePermissionStore()
    const current = await fetchCurrentUser()
    user.value = current.user
    mustChangePassword.value = current.must_change_password

    const permissions = await fetchPermissions()
    permissionStore.applyPermissions({
      permissions: permissions.permissions,
      menus: permissions.menus,
      is_super_admin: permissions.is_super_admin,
    })
  }

  /** Sign in and load the session. */
  async function signIn(payload: LoginRequest): Promise<void> {
    const result = await loginRequest(payload)
    writeCredentials(result.token)
    mustChangePassword.value = result.must_change_password
    sessionEnded.value = false
    await loadSession()
  }

  /** Sign out, telling the backend first so the session is revoked. */
  async function signOut(): Promise<void> {
    try {
      if (readCredentials() !== null) {
        await logoutRequest()
      }
    } catch {
      // A failed revoke must not trap the operator inside the session.
    } finally {
      resetSession()
    }
  }

  /** Forget every trace of the session. */
  function resetSession(): void {
    const permissionStore = usePermissionStore()
    clearCredentials()
    user.value = null
    mustChangePassword.value = false
    permissionStore.reset()
  }

  /** Restore the session on a cold start, if credentials survived. */
  async function restore(): Promise<void> {
    if (initialising.value) {
      return
    }
    initialising.value = true
    try {
      if (readCredentials() === null) {
        return
      }
      await loadSession()
    } catch {
      resetSession()
    } finally {
      initialising.value = false
      ready.value = true
    }
  }

  /** Wire the "the refresh token is gone" signal into the store. */
  function bindSessionExpiry(): void {
    onSessionExpired(() => {
      sessionEnded.value = true
      resetSession()
    })
  }

  /** End the session locally (used after a refresh failure). */
  function forceEndSession(): void {
    sessionEnded.value = true
    endSession()
  }

  return {
    user,
    mustChangePassword,
    initialising,
    ready,
    sessionEnded,
    isAuthenticated,
    displayName,
    username,
    isSuperAdmin,
    loadSession,
    signIn,
    signOut,
    resetSession,
    restore,
    bindSessionExpiry,
    forceEndSession,
  }
})
