/**
 * Session endpoints (`app/admin/auth`).
 *
 * The console has no user directory of its own: it authenticates against the
 * same administrator directory as the management platform, so the four calls
 * below are the whole session surface.
 *
 * `login` is anonymous by definition; the rest skip the refresh-and-replay
 * retry because a 401 on `/me` or `/permissions` *is* the answer — replaying
 * them would only delay the redirect to the login page.
 */

import { get, post } from '@/api/client'
import type {
  CurrentUserResponse,
  LoginRequest,
  LoginResult,
  PermissionsResponse,
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

/**
 * `GET /admin/auth/permissions`
 *
 * Returns every menu node the caller holds, ops nodes included. This console
 * renders only its own branch — see `OPS_MENU_FILTER` in `@/router/route-builder`.
 */
export function fetchPermissions(): Promise<PermissionsResponse> {
  return get<PermissionsResponse>('/admin/auth/permissions', {
    vctn: { skipAuthRetry: true },
  })
}
