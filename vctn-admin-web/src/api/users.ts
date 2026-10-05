/** Administrator account management (`app/admin/users`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type { AdminResetPasswordRequest, ResetPasswordResult } from '@/types/auth'
import type {
  AdminUser,
  AssignRolesRequest,
  BatchForceLogoutRequest,
  CreateUserRequest,
  DepartmentUserRow,
  ForceLogoutRequest,
  ForceLogoutResult,
  MoveDepartmentRequest,
  OnlineUser,
  RoleBrief,
  UpdateUserRequest,
  UserListQuery,
  UserSessionRow,
} from '@/types/system'

/** `GET /admin/users` */
export function listUsers(query: UserListQuery = {}): Promise<Page<AdminUser>> {
  return get<Page<AdminUser>>('/admin/users', { params: query })
}

/** `POST /admin/users` */
export function createUser(payload: CreateUserRequest): Promise<AdminUser> {
  return post<AdminUser>('/admin/users', payload, {
    vctn: { idempotencyKey: `create-user:${payload.username}` },
  })
}

/** `GET /admin/users/{user_id}` */
export function getUser(userId: string): Promise<AdminUser> {
  return get<AdminUser>(`/admin/users/${userId}`)
}

/** `PUT /admin/users/{user_id}` */
export function updateUser(userId: string, payload: UpdateUserRequest): Promise<AdminUser> {
  return put<AdminUser>(`/admin/users/${userId}`, payload)
}

/** `DELETE /admin/users/{user_id}` (logical delete) */
export function deleteUser(userId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/users/${userId}`)
}

/** `POST /admin/users/{user_id}/enable` */
export function enableUser(userId: string): Promise<AdminUser> {
  return post<AdminUser>(`/admin/users/${userId}/enable`)
}

/** `POST /admin/users/{user_id}/disable` */
export function disableUser(userId: string): Promise<AdminUser> {
  return post<AdminUser>(`/admin/users/${userId}/disable`)
}

/** `POST /admin/users/{user_id}/reset-password` */
export function resetUserPassword(
  userId: string,
  payload: AdminResetPasswordRequest,
): Promise<ResetPasswordResult> {
  return post<ResetPasswordResult>(`/admin/users/${userId}/reset-password`, payload)
}

/** `GET /admin/users/{user_id}/roles` */
export function getUserRoles(userId: string): Promise<RoleBrief[]> {
  return get<RoleBrief[]>(`/admin/users/${userId}/roles`)
}

/** `PUT /admin/users/{user_id}/roles` */
export function assignUserRoles(userId: string, payload: AssignRolesRequest): Promise<RoleBrief[]> {
  return put<RoleBrief[]>(`/admin/users/${userId}/roles`, payload)
}

/** `PUT /admin/users/{user_id}/department` */
export function moveUserDepartment(
  userId: string,
  payload: MoveDepartmentRequest,
): Promise<AdminUser> {
  return put<AdminUser>(`/admin/users/${userId}/department`, payload)
}

/** `GET /admin/users/{user_id}/sessions` */
export function getUserSessions(userId: string): Promise<UserSessionRow[]> {
  return get<UserSessionRow[]>(`/admin/users/${userId}/sessions`)
}

/** `POST /admin/users/{user_id}/force-logout` */
export function forceLogout(userId: string, payload: ForceLogoutRequest): Promise<ForceLogoutResult> {
  return post<ForceLogoutResult>(`/admin/users/${userId}/force-logout`, payload)
}

/** `POST /admin/users/batch-force-logout` */
export function batchForceLogout(
  payload: BatchForceLogoutRequest,
): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>('/admin/users/batch-force-logout', payload)
}

/** `GET /admin/users/online` */
export function listOnlineUsers(): Promise<OnlineUser[]> {
  return get<OnlineUser[]>('/admin/users/online')
}

/** `GET /admin/departments/{department_id}/users` */
export function listDepartmentUsers(departmentId: string): Promise<DepartmentUserRow[]> {
  return get<DepartmentUserRow[]>(`/admin/departments/${departmentId}/users`)
}
