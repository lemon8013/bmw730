/** File administration (`app/system/files`). */

import axios from 'axios'

import { del, get, post } from '@/api/client'
import { apiBaseUrl } from '@/api/endpoint'
import type { Page } from '@/types/api'
import type {
  FileCreateRequest,
  FileCreated,
  FileDownloadUrl,
  FileQuery,
  FileRecord,
  UploadIntent,
  UploadIntentRequest,
} from '@/types/ops'

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

/** `DELETE /files/{file_id}` — logical delete, removes the object too. */
export function deleteFile(fileId: string): Promise<FileRecord> {
  return del<FileRecord>(`/files/${fileId}`)
}

/**
 * `POST /files/upload-intent` — reserves the object key and answers where the
 * bytes have to go. Nothing has been uploaded when this resolves.
 */
export function createUploadIntent(payload: UploadIntentRequest): Promise<UploadIntent> {
  return post<UploadIntent>('/files/upload-intent', payload)
}

/**
 * `POST /files/{file_id}/confirm` — checks that a direct upload really landed.
 * A row whose bytes never arrive is retired by the backend instead of lying to
 * the next listing.
 */
export function confirmUpload(fileId: string): Promise<FileRecord> {
  return post<FileRecord>(`/files/${fileId}/confirm`)
}

/**
 * Upload bytes for an already reserved record.
 *
 * Pre-signed URLs are absolute and must be used without our interceptors
 * or credentials - sending an Authorization header to the object store leaks
 * the admin token - so the direct path uses a bare axios instance. Local
 * storage has no pre-signature and goes through the ordinary client.
 */
export async function uploadFileContent(
  intent: UploadIntent,
  file: Blob,
  contentType: string,
): Promise<void> {
  if (intent.mode === 'direct') {
    await axios.put(intent.upload_url, file, {
      headers: { ...intent.headers, 'Content-Type': contentType },
    })
    return
  }
  await post(`/files/${intent.id}/content`, file, {
    headers: { 'Content-Type': contentType },
  })
}

/** `GET /files/{file_id}/download-url` */
export function getDownloadUrl(fileId: string, inline = false): Promise<FileDownloadUrl> {
  return get<FileDownloadUrl>(`/files/${fileId}/download-url`, { params: { inline } })
}

/** Path used when the backend has to proxy the bytes (local storage). */
export function proxiedContentUrl(fileId: string): string {
  return `${apiBaseUrl}/files/${fileId}/content`
}
