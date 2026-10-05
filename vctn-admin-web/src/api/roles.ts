/** Role and role-inheritance management (`app/admin/roles`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  AssignParentsRequest,
  AssignPermissionsRequest,
  CreateRoleRequest,
  ParentRoleBrief,
  PermissionBrief,
  Role,
  UpdateRoleRequest,
} from '@/types/system'

/** `GET /admin/roles` */
export function listRoles(page = 1, pageSize = 200): Promise<Page<Role>> {
  return get<Page<Role>>('/admin/roles', { params: { page, page_size: pageSize } })
}

/** `POST /admin/roles` */
export function createRole(payload: CreateRoleRequest): Promise<Role> {
  return post<Role>('/admin/roles', payload, {
    vctn: { idempotencyKey: `create-role:${payload.role_code}` },
  })
}

/** `GET /admin/roles/{role_id}` */
export function getRole(roleId: string): Promise<Role> {
  return get<Role>(`/admin/roles/${roleId}`)
}

/** `PUT /admin/roles/{role_id}` */
export function updateRole(roleId: string, payload: UpdateRoleRequest): Promise<Role> {
  return put<Role>(`/admin/roles/${roleId}`, payload)
}

/** `DELETE /admin/roles/{role_id}` */
export function deleteRole(roleId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/roles/${roleId}`)
}

/** `GET /admin/roles/{role_id}/permissions` */
export function getRolePermissions(roleId: string): Promise<PermissionBrief[]> {
  return get<PermissionBrief[]>(`/admin/roles/${roleId}/permissions`)
}

/** `PUT /admin/roles/{role_id}/permissions` */
export function assignRolePermissions(
  roleId: string,
  payload: AssignPermissionsRequest,
): Promise<PermissionBrief[]> {
  return put<PermissionBrief[]>(`/admin/roles/${roleId}/permissions`, payload)
}

/** `GET /admin/roles/{role_id}/parents` */
export function getRoleParents(roleId: string): Promise<ParentRoleBrief[]> {
  return get<ParentRoleBrief[]>(`/admin/roles/${roleId}/parents`)
}

/** `PUT /admin/roles/{role_id}/parents` */
export function assignRoleParents(
  roleId: string,
  payload: AssignParentsRequest,
): Promise<ParentRoleBrief[]> {
  return put<ParentRoleBrief[]>(`/admin/roles/${roleId}/parents`, payload)
}
