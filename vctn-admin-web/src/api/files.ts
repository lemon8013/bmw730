/** File metadata administration (`app/system/files`). */

import { del, get, post } from '@/api/client'
import type { Page } from '@/types/api'
import type { FileCreateRequest, FileCreated, FileQuery, FileRecord } from '@/types/ops'

/** `GET /files` */
export function listFiles(query: FileQuery = {}): Promise<Page<FileRecord>> {
  return get<Page<FileRecord>>('/files', { params: query })
}

/** `GET /files/{file_id}` */
export function getFile(fileId: string): Promise<FileRecord> {
  return get<FileRecord>(`/files/${fileId}`)
}

/** `POST /files` — registers metadata for an already stored object. */
export function createFileRecord(payload: FileCreateRequest): Promise<FileCreated> {
  return post<FileCreated>('/files', payload, {
    vctn: { idempotencyKey: `file-record:${payload.object_key}` },
  })
}

/** `DELETE /files/{file_id}` — logical delete. */
export function deleteFile(fileId: string): Promise<FileRecord> {
  return del<FileRecord>(`/files/${fileId}`)
}
