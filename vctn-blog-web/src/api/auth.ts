/**
 * Platform (business user) authentication calls.
 *
 * Registering and signing in are anonymous by definition; the shared client
 * attaches a Bearer token when a session exists, which is what makes `me` and
 * `logout` personal.
 */

import { httpClient } from '@/api/client'
import type { ApiEnvelope } from '@/types/api'
import type { LoginRequest, LoginResult, PlatformUser, RegisterRequest } from '@/types/auth'

/** Create a business user account. Returns the created user, not a session. */
export async function register(payload: RegisterRequest): Promise<PlatformUser> {
  const response = await httpClient.post<ApiEnvelope<PlatformUser>>('/auth/register', payload)
  return response.data.data as PlatformUser
}

/** Sign in by username, email or phone. */
export async function login(payload: LoginRequest): Promise<LoginResult> {
  const response = await httpClient.post<ApiEnvelope<LoginResult>>('/auth/login', payload)
  return response.data.data as LoginResult
}

/** Ask the backend to revoke the current session. */
export async function logout(): Promise<void> {
  await httpClient.post<ApiEnvelope<Record<string, never>>>('/auth/logout', {})
}

/** Read the identity behind the current token. */
export async function fetchCurrentUser(): Promise<PlatformUser> {
  const response = await httpClient.get<ApiEnvelope<PlatformUser>>('/auth/me')
  return response.data.data as PlatformUser
}
