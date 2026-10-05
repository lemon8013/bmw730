/**
 * RBAC and system configuration payloads, matching the FastAPI schemas one to
 * one. Nothing is added that the backend does not return.
 */

import type { EntityId, IsoDateTime } from '@/types/api'

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

/** `RoleBrief`. */
export interface RoleBrief {
  id: EntityId
  role_code: string
  role_name: string
  data_scope: string
}

/** `UserResponse`. */
export interface AdminUser {
  id: EntityId
  username: string
  display_name: string
  email?: string | null
  phone?: string | null
  department_id?: EntityId | null
  department_name?: string | null
  status: string
  is_super_admin: boolean
  must_change_password: boolean
  password_changed_at?: IsoDateTime | null
  password_expires_at?: IsoDateTime | null
  failed_login_count: number
  locked_until?: IsoDateTime | null
  last_login_at?: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
  roles?: RoleBrief[]
  temporary_password?: string | null
}

/** `CreateUserRequest`. */
export interface CreateUserRequest {
  username: string
  display_name: string
  email?: string | null
  phone?: string | null
  department_id?: EntityId | null
  role_ids?: EntityId[]
  temporary_password?: string | null
}

/** `UpdateUserRequest`. */
export interface UpdateUserRequest {
  display_name?: string | null
  email?: string | null
  phone?: string | null
  status?: string | null
  department_id?: EntityId | null
}

/** `MoveDepartmentRequest`. */
export interface MoveDepartmentRequest {
  department_id?: EntityId | null
}

/** `AssignRolesRequest`. */
export interface AssignRolesRequest {
  role_ids?: EntityId[]
}

/** `ForceLogoutRequest`. */
export interface ForceLogoutRequest {
  reason?: string | null
}

/** `ForceLogoutResponse`. */
export interface ForceLogoutResult {
  user_id: EntityId
  revoked_sessions: number
}

/** `BatchForceLogoutRequest`. */
export interface BatchForceLogoutRequest {
  user_ids?: EntityId[]
  reason?: string | null
}

/** `OnlineUserResponse`. */
export interface OnlineUser {
  user_id: EntityId
  username: string
  display_name: string
  department_id?: EntityId | null
  session_id: EntityId
  ip?: string | null
  device_type?: string | null
  login_at: IsoDateTime
  last_active_at?: IsoDateTime | null
}

/** `GET /admin/users/{user_id}/sessions` returns an untyped list of objects. */
export interface UserSessionRow {
  session_id?: EntityId | string
  id?: EntityId | string
  status?: string
  ip?: string | null
  device_type?: string | null
  user_agent?: string | null
  login_at?: IsoDateTime | null
  last_active_at?: IsoDateTime | null
  expires_at?: IsoDateTime | null
  revoked_at?: IsoDateTime | null
  revoke_reason?: string | null
  [key: string]: unknown
}

/** `GET /admin/departments/{id}/users` returns an untyped list of objects. */
export interface DepartmentUserRow {
  id?: EntityId | string
  username?: string
  display_name?: string
  status?: string
  [key: string]: unknown
}

/** Query parameters of `GET /admin/users`. */
export interface UserListQuery {
  keyword?: string
  department_id?: EntityId
  status?: string
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// Departments
// ---------------------------------------------------------------------------

/** `DepartmentResponse`. */
export interface Department {
  id: EntityId
  parent_id?: EntityId | null
  department_code: string
  department_name: string
  status: string
  sort_order: number
  description?: string | null
  user_count?: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `DepartmentTreeNode`. */
export interface DepartmentTreeNode {
  id: EntityId
  parent_id?: EntityId | null
  department_code: string
  department_name: string
  status: string
  sort_order: number
  user_count?: number
  children?: DepartmentTreeNode[]
}

/** `CreateDepartmentRequest`. */
export interface CreateDepartmentRequest {
  department_code: string
  department_name: string
  parent_id?: EntityId | null
  sort_order?: number
  description?: string | null
}

/** `UpdateDepartmentRequest`. */
export interface UpdateDepartmentRequest {
  department_name?: string | null
  parent_id?: EntityId | null
  sort_order?: number | null
  description?: string | null
  status?: string | null
}

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

/** `RoleResponse`. */
export interface Role {
  id: EntityId
  role_code: string
  role_name: string
  description?: string | null
  status: string
  data_scope: string
  custom_department_ids?: EntityId[]
  user_count?: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CreateRoleRequest`. */
export interface CreateRoleRequest {
  role_code: string
  role_name: string
  description?: string | null
  data_scope?: string
  custom_department_ids?: EntityId[]
}

/** `UpdateRoleRequest`. */
export interface UpdateRoleRequest {
  role_name?: string | null
  description?: string | null
  status?: string | null
  data_scope?: string | null
  custom_department_ids?: EntityId[] | null
}

/** `ParentRoleBrief`. */
export interface ParentRoleBrief {
  id: EntityId
  role_code: string
  role_name: string
  data_scope: string
}

/** `AssignParentsRequest`. */
export interface AssignParentsRequest {
  parent_role_ids?: EntityId[]
}

/** `PermissionBrief`. */
export interface PermissionBrief {
  id: EntityId
  permission_code: string
  permission_name: string
  permission_type: string
  resource_type: string
  resource_code: string
}

/** `AssignPermissionsRequest`. */
export interface AssignPermissionsRequest {
  permission_ids?: EntityId[]
}

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

/** `PermissionTreeNode`. */
export interface PermissionTreeNode {
  id: EntityId
  permission_code: string
  permission_name: string
  permission_type: string
  resource_type: string
  resource_code: string
  status: string
  sort_order: number
  children?: PermissionTreeNode[]
}

/** `FieldPermissionOutput`. */
export interface FieldPermissionOutput {
  id: EntityId
  field_code: string
  field_mode: string
}

/** `FieldPermissionInput`. */
export interface FieldPermissionInput {
  field_code: string
  field_mode: string
}

/** `PermissionResourceResponse`. */
export interface PermissionResource {
  id: EntityId
  permission_code: string
  permission_name: string
  permission_type: string
  resource_type: string
  resource_code: string
  parent_id?: EntityId | null
  status: string
  sort_order: number
  description?: string | null
  field_permissions?: FieldPermissionOutput[]
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CreateResourceRequest`. */
export interface CreateResourceRequest {
  permission_code: string
  permission_name: string
  permission_type: string
  resource_type: string
  resource_code: string
  parent_id?: EntityId | null
  sort_order?: number
  description?: string | null
  field_permissions?: FieldPermissionInput[]
}

/** `UpdateResourceRequest`. */
export interface UpdateResourceRequest {
  permission_name?: string | null
  resource_type?: string | null
  resource_code?: string | null
  parent_id?: EntityId | null
  sort_order?: number | null
  status?: string | null
  description?: string | null
  field_permissions?: FieldPermissionInput[] | null
}

// ---------------------------------------------------------------------------
// Dictionaries
// ---------------------------------------------------------------------------

/** `DictTypeResponse`. */
export interface DictType {
  id: EntityId
  dict_code: string
  dict_name: string
  description?: string | null
  status: string
  item_count?: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `DictItemResponse`. */
export interface DictItem {
  id: EntityId
  dict_type_id: EntityId
  item_label: string
  item_value: string
  item_code?: string | null
  sort_order: number
  status: string
  is_default: boolean
  description?: string | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CreateDictTypeRequest`. */
export interface CreateDictTypeRequest {
  dict_code: string
  dict_name: string
  description?: string | null
}

/** `UpdateDictTypeRequest`. */
export interface UpdateDictTypeRequest {
  dict_name?: string | null
  description?: string | null
  status?: string | null
}

/** `CreateDictItemRequest`. */
export interface CreateDictItemRequest {
  item_label: string
  item_value: string
  item_code?: string | null
  sort_order?: number
  is_default?: boolean
  description?: string | null
}

/** `UpdateDictItemRequest`. */
export interface UpdateDictItemRequest {
  item_label?: string | null
  item_value?: string | null
  item_code?: string | null
  sort_order?: number | null
  is_default?: boolean | null
  status?: string | null
  description?: string | null
}

// ---------------------------------------------------------------------------
// Config / Feature flags
// ---------------------------------------------------------------------------

/** `ConfigResponse`. */
export interface SystemConfig {
  id: EntityId
  config_key: string
  config_name: string
  config_group?: string | null
  value_type: string
  config_value?: string | null
  default_value?: string | null
  editable: boolean
  requires_restart: boolean
  status: string
  description?: string | null
  version: number
  effective_at?: IsoDateTime | null
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `UpdateConfigRequest`. */
export interface UpdateConfigRequest {
  config_value: string
  reason?: string | null
}

/** `FeatureFlagResponse`. */
export interface FeatureFlag {
  id: EntityId
  flag_key: string
  flag_name: string
  enabled: boolean
  strategy: string
  percentage: number
  conditions?: Record<string, unknown> | null
  description?: string | null
  version: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

/** `CreateFeatureFlagRequest`. */
export interface CreateFeatureFlagRequest {
  flag_key: string
  flag_name: string
  enabled?: boolean
  strategy?: string
  percentage?: number
  conditions?: Record<string, unknown> | null
  description?: string | null
}

/** `UpdateFeatureFlagRequest`. */
export interface UpdateFeatureFlagRequest {
  flag_name?: string | null
  strategy?: string | null
  percentage?: number | null
  conditions?: Record<string, unknown> | null
  description?: string | null
}
