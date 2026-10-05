/**
 * API layer.
 *
 * One module per backend tag group, all sharing the client in
 * `@/api/client`. Nothing here invents an endpoint: every function maps to a
 * path the running FastAPI application exposes.
 */

export { ApiError, TRANSPORT_CODE } from '@/api/errors'
export { apiBaseUrl, appCode, appVersion } from '@/api/endpoint'
export { clearCredentials, readCredentials, writeCredentials } from '@/api/credentials'
export { endSession, onSessionExpired, refreshTokens } from '@/api/refresh'
export { del, get, httpClient, post, put, request, type RequestOptions } from '@/api/client'
