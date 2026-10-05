/**
 * Authentication and authorization payloads, matching `app/admin/auth/schema.py`
 * and `app/shared/authorization/*` exactly.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

/** Issued credential pair (`TokenResponse`). */
export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in: number
}

/** Administrator login payload (`LoginRequest`). */
export interface LoginRequest {
  username: string
  password: string
}

/** Administrator login result (`LoginResponse`). */
export interface LoginResult {
  token: TokenPair
  must_change_password: boolean
  password_expired: boolean
}

/** Refresh payload (`RefreshRequest`). The token travels in the body. */
export interface RefreshRequest {
  refresh_token: string
}

/** Self service password change (`ChangePasswordRequest`). */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

/** Administrative password reset (`ResetPasswordRequest`). */
export interface AdminResetPasswordRequest {
  user_id: EntityId
  reason?: string | null
}

/** Result of an administrative reset (`ResetPasswordResponse`). */
export interface ResetPasswordResult {
  user_id: EntityId
  temporary_password: string
  must_change_password: boolean
}

/** The administrator behind the current session (`AdminUserBrief`). */
export interface AdminUserBrief {
  id: EntityId
  username: string
  display_name: string
  email?: string | null
  phone?: string | null
  department_id?: EntityId | null
  status: string
  is_super_admin: boolean
  must_change_password: boolean
  last_login_at?: IsoDateTime | null
  created_at: IsoDateTime
}

/** `/auth/me` payload. */
export interface CurrentUserResponse {
  user: AdminUserBrief
  permissions: string[]
  is_super_admin: boolean
  must_change_password: boolean
  password_expired: boolean
}

/** One node of the dynamic menu tree (`MenuNode`). */
export interface MenuNode {
  id: EntityId
  permission_code: string
  permission_name: string
  resource_type: string
  resource_code: string
  parent_id?: EntityId | null
  sort_order: number
}

/** `/auth/permissions` payload. */
export interface PermissionsResponse {
  permissions: string[]
  menus: MenuNode[]
  is_super_admin: boolean
}
