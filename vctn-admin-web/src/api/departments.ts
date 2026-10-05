/** Department management (`app/admin/departments`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateDepartmentRequest,
  Department,
  DepartmentTreeNode,
  UpdateDepartmentRequest,
} from '@/types/system'

/** `GET /admin/departments` */
export function listDepartments(page = 1, pageSize = 200): Promise<Page<Department>> {
  return get<Page<Department>>('/admin/departments', {
    params: { page, page_size: pageSize },
  })
}

/** `GET /admin/departments/tree` */
export function fetchDepartmentTree(): Promise<DepartmentTreeNode[]> {
  return get<DepartmentTreeNode[]>('/admin/departments/tree')
}

/** `GET /admin/departments/{department_id}` */
export function getDepartment(departmentId: string): Promise<Department> {
  return get<Department>(`/admin/departments/${departmentId}`)
}

/** `POST /admin/departments` */
export function createDepartment(payload: CreateDepartmentRequest): Promise<Department> {
  return post<Department>('/admin/departments', payload, {
    vctn: { idempotencyKey: `create-department:${payload.department_code}` },
  })
}

/** `PUT /admin/departments/{department_id}` */
export function updateDepartment(
  departmentId: string,
  payload: UpdateDepartmentRequest,
): Promise<Department> {
  return put<Department>(`/admin/departments/${departmentId}`, payload)
}

/** `DELETE /admin/departments/{department_id}` */
export function deleteDepartment(departmentId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/departments/${departmentId}`)
}

/** `GET /admin/departments/{department_id}/children` */
export function listDepartmentChildren(departmentId: string): Promise<Department[]> {
  return get<Department[]>(`/admin/departments/${departmentId}/children`)
}
