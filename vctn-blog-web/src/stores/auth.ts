/**
 * Business user session state.
 *
 * The blog is readable anonymously; signing in unlocks commenting, liking and
 * authoring. The store owns that lifecycle; tokens themselves live in
 * `@/api/credentials` and are never read here.
 */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from '@/api/auth'
import { clearCredentials, readCredentials, writeCredentials } from '@/api/credentials'
import { endSession, onSessionExpired } from '@/api/session'
import type { LoginRequest, PlatformUser, RegisterRequest } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = shallowRef<PlatformUser | null>(null)
  const initialising = ref(false)
  const ready = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const displayName = computed(() => user.value?.nickname ?? user.value?.username ?? '未登录')
  const username = computed(() => user.value?.username ?? '')
  const userId = computed(() => user.value?.id ?? null)

  /** Load the identity behind the stored credentials. */
  async function loadSession(): Promise<void> {
    user.value = await fetchCurrentUser()
  }

  /** Sign in and load the session. */
  async function signIn(payload: LoginRequest): Promise<void> {
    const result = await loginRequest(payload)
    writeCredentials(result.token)
    await loadSession()
  }

  /** Create an account. The backend does not issue a session, so sign in next. */
  async function signUp(payload: RegisterRequest): Promise<void> {
    await registerRequest(payload)
  }

  /** Sign out, telling the backend first so the session is revoked. */
  async function signOut(): Promise<void> {
    try {
      if (readCredentials() !== null) {
        await logoutRequest()
      }
    } catch {
      // A failed revoke must not trap the user inside the session.
    } finally {
      resetSession()
    }
  }

  /** Forget every trace of the session. */
  function resetSession(): void {
    clearCredentials()
    user.value = null
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
      resetSession()
    })
  }

  /** Drop the session without involving the backend. */
  function dropSession(): void {
    endSession()
  }

  return {
    user,
    ready,
    isAuthenticated,
    displayName,
    username,
    userId,
    signIn,
    signUp,
    signOut,
    resetSession,
    restore,
    bindSessionExpiry,
    dropSession,
  }
})
