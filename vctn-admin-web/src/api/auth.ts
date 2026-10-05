/** Administrator authentication (`app/admin/auth`). */

import { get, post } from '@/api/client'
import type {
  AdminResetPasswordRequest,
  ChangePasswordRequest,
  CurrentUserResponse,
  LoginRequest,
  LoginResult,
  PermissionsResponse,
  ResetPasswordResult,
} from '@/types/auth'

/** `POST /admin/auth/login` */
export function login(payload: LoginRequest): Promise<LoginResult> {
  return post<LoginResult>('/admin/auth/login', payload, {
    vctn: { anonymous: true, skipAuthRetry: true },
  })
}

/** `POST /admin/auth/logout` */
export function logout(): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>('/admin/auth/logout', undefined, {
    vctn: { skipAuthRetry: true },
  })
}

/** `GET /admin/auth/me` */
export function fetchCurrentUser(): Promise<CurrentUserResponse> {
  return get<CurrentUserResponse>('/admin/auth/me', { vctn: { skipAuthRetry: true } })
}

/** `GET /admin/auth/permissions` */
export function fetchPermissions(): Promise<PermissionsResponse> {
  return get<PermissionsResponse>('/admin/auth/permissions', {
    vctn: { skipAuthRetry: true },
  })
}

/** `POST /admin/auth/change-password` */
export function changePassword(payload: ChangePasswordRequest): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>('/admin/auth/change-password', payload)
}

/** `POST /admin/auth/reset-password` */
export function adminResetPassword(
  payload: AdminResetPasswordRequest,
): Promise<ResetPasswordResult> {
  return post<ResetPasswordResult>('/admin/auth/reset-password', payload, {
    vctn: { idempotencyKey: `reset-password:${payload.user_id}` },
  })
}
