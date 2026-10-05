/** Dictionary administration (`app/admin/dictionaries`). */

import { del, get, post, put } from '@/api/client'
import type { Page } from '@/types/api'
import type {
  CreateDictItemRequest,
  CreateDictTypeRequest,
  DictItem,
  DictType,
  UpdateDictItemRequest,
  UpdateDictTypeRequest,
} from '@/types/system'

/** `GET /admin/dictionaries/types` */
export function listDictTypes(page = 1, pageSize = 100): Promise<Page<DictType>> {
  return get<Page<DictType>>('/admin/dictionaries/types', {
    params: { page, page_size: pageSize },
  })
}

/** `POST /admin/dictionaries/types` */
export function createDictType(payload: CreateDictTypeRequest): Promise<DictType> {
  return post<DictType>('/admin/dictionaries/types', payload, {
    vctn: { idempotencyKey: `create-dict-type:${payload.dict_code}` },
  })
}

/** `PUT /admin/dictionaries/types/{type_id}` */
export function updateDictType(typeId: string, payload: UpdateDictTypeRequest): Promise<DictType> {
  return put<DictType>(`/admin/dictionaries/types/${typeId}`, payload)
}

/** `DELETE /admin/dictionaries/types/{type_id}` */
export function deleteDictType(typeId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/dictionaries/types/${typeId}`)
}

/** `GET /admin/dictionaries/types/{type_id}/items` */
export function listDictItems(typeId: string): Promise<DictItem[]> {
  return get<DictItem[]>(`/admin/dictionaries/types/${typeId}/items`)
}

/** `POST /admin/dictionaries/types/{type_id}/items` */
export function createDictItem(
  typeId: string,
  payload: CreateDictItemRequest,
): Promise<DictItem> {
  return post<DictItem>(`/admin/dictionaries/types/${typeId}/items`, payload, {
    vctn: { idempotencyKey: `create-dict-item:${typeId}:${payload.item_value}` },
  })
}

/** `PUT /admin/dictionaries/items/{item_id}` */
export function updateDictItem(
  itemId: string,
  payload: UpdateDictItemRequest,
): Promise<DictItem> {
  return put<DictItem>(`/admin/dictionaries/items/${itemId}`, payload)
}

/** `DELETE /admin/dictionaries/items/{item_id}` */
export function deleteDictItem(itemId: string): Promise<Record<string, unknown>> {
  return del<Record<string, unknown>>(`/admin/dictionaries/items/${itemId}`)
}
