/**
 * Platform (business user) authentication calls.
 *
 * Every endpoint here is anonymous: registering and signing in obviously cannot
 * require credentials. The shared client attaches a Bearer token when a session
 * exists, which is what makes `me` / `logout` / `changePassword` personal.
 */

import { httpClient } from '@/api/client'
import type { ApiEnvelope } from '@/types/api'
import type {
  ChangePasswordRequest,
  LoginRequest,
  LoginResult,
  PlatformUser,
  RegisterRequest,
  TokenPair,
} from '@/types/auth'

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

/** Exchange a refresh token for a new pair. Used by the session module. */
export async function refresh(refreshToken: string): Promise<TokenPair> {
  const response = await httpClient.post<ApiEnvelope<TokenPair>>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return response.data.data as TokenPair
}

/** Change the signed-in account's own password. */
export async function changePassword(payload: ChangePasswordRequest): Promise<void> {
  await httpClient.post<ApiEnvelope<Record<string, never>>>('/auth/change-password', payload)
}
