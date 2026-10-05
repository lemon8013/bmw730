/**
 * Foundation tests for the admin console.
 *
 * They pin the parts of the shell that every page depends on: the axios client
 * contract (trace headers, envelope unwrapping, error normalisation), the safe
 * return-URL rule, and the permission projection that turns the backend menu
 * into routes.
 */

import { AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { apiBaseUrl } from '@/api/endpoint'
import { ApiError, TRANSPORT_CODE } from '@/api/errors'
import { httpClient } from '@/api/client'
import { projectMenu } from '@/router/route-builder'
import { safeReturnPath } from '@/router/guards'
import { PAGE_TABLE, resolvePage } from '@/router/route-table'
import { useAppStore } from '@/stores/app'
import type { MenuNode } from '@/types/auth'

const adapterRestorers: Array<() => void> = []

function respondWith(data: unknown): void {
  const original = httpClient.defaults.adapter
  httpClient.defaults.adapter = async (
    config: InternalAxiosRequestConfig,
  ): Promise<AxiosResponse> => ({
    data,
    status: 200,
    statusText: 'OK',
    headers: new AxiosHeaders(),
    config,
  })
  adapterRestorers.push(() => {
    httpClient.defaults.adapter = original
  })
}

describe('admin console shell', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    while (adapterRestorers.length > 0) {
      adapterRestorers.pop()?.()
    }
  })

  it('initialises the application store', () => {
    const store = useAppStore()
    expect(store.applicationName).toBe('VCTN 管理平台')
    expect(store.apiPrefix).toBe(apiBaseUrl)
  })

  it('creates the axios instance with the configured base url', () => {
    expect(httpClient.defaults.baseURL).toBe(apiBaseUrl)
    expect(typeof httpClient.interceptors.request.use).toBe('function')
    expect(typeof httpClient.interceptors.response.use).toBe('function')
  })

  it('attaches trace headers and accepts a success envelope', async () => {
    const original = httpClient.defaults.adapter
    let captured: InternalAxiosRequestConfig | undefined
    httpClient.defaults.adapter = async (
      config: InternalAxiosRequestConfig,
    ): Promise<AxiosResponse> => {
      captured = config
      return {
        data: { code: 0, message: 'success', data: { ok: true } },
        status: 200,
        statusText: 'OK',
        headers: new AxiosHeaders(),
        config,
      }
    }

    const response = await httpClient.get('/probe')

    expect(response.data.code).toBe(0)
    expect(captured?.headers.get('X-Trace-ID')).toBeTruthy()
    expect(captured?.headers.get('X-Request-ID')).toBeTruthy()

    httpClient.defaults.adapter = original
  })

  it('rejects a non-zero envelope code with an ApiError', async () => {
    respondWith({ code: 403001, message: 'permission denied', data: null })
    const failure: unknown = await httpClient.get('/probe').catch((error: unknown) => error)
    expect(failure).toBeInstanceOf(ApiError)
    expect((failure as ApiError).isForbidden).toBe(true)
  })

  it('normalises a transport failure', async () => {
    const original = httpClient.defaults.adapter
    httpClient.defaults.adapter = async (): Promise<AxiosResponse> => {
      throw new Error('connection refused')
    }
    const failure: unknown = await httpClient.get('/probe').catch((error: unknown) => error)
    expect(failure).toBeInstanceOf(ApiError)
    expect((failure as ApiError).code).toBe(TRANSPORT_CODE.network)
    httpClient.defaults.adapter = original
  })

  it('rejects an envelope that is not the unified shape', async () => {
    respondWith({ unexpected: true })
    const failure: unknown = await httpClient.get('/probe').catch((error: unknown) => error)
    expect(failure).toBeInstanceOf(ApiError)
    expect((failure as ApiError).code).toBe(TRANSPORT_CODE.malformed)
  })

  it('never lets a return url leave the application', () => {
    expect(safeReturnPath('/system/users')).toBe('/system/users')
    expect(safeReturnPath('//evil.example.com')).toBeNull()
    expect(safeReturnPath('https://evil.example.com')).toBeNull()
    expect(safeReturnPath('system/users')).toBeNull()
    expect(safeReturnPath('\\\\server\\share')).toBeNull()
    expect(safeReturnPath(undefined)).toBeNull()
    expect(safeReturnPath(42)).toBeNull()
  })

  it('maps every wired page onto a unique route path and name', () => {
    const paths = Object.values(PAGE_TABLE).map((page) => page.path)
    const names = Object.values(PAGE_TABLE).map((page) => page.name)
    expect(new Set(paths).size).toBe(paths.length)
    expect(new Set(names).size).toBe(names.length)
  })

  it('resolves a wired permission code and refuses an unknown one', () => {
    expect(resolvePage('PAGE_USER')?.path).toBe('/system/users')
    expect(resolvePage('PAGE_NOT_WIRED')).toBeNull()
  })

  it('projects the backend menu onto routes and reports unwired codes', () => {
    const menus: MenuNode[] = [
      {
        id: '1',
        permission_code: 'MENU_SYSTEM',
        permission_name: '系统管理',
        resource_type: 'MENU',
        resource_code: 'MENU_SYSTEM',
        parent_id: null,
        sort_order: 10,
      },
      {
        id: '2',
        permission_code: 'PAGE_USER',
        permission_name: '用户管理',
        resource_type: 'PAGE',
        resource_code: 'PAGE_USER',
        parent_id: '1',
        sort_order: 11,
      },
      {
        id: '3',
        permission_code: 'PAGE_NOT_WIRED',
        permission_name: '未接入页',
        resource_type: 'PAGE',
        resource_code: 'PAGE_NOT_WIRED',
        parent_id: '1',
        sort_order: 12,
      },
    ]

    const projected = projectMenu(menus, (code) => code !== 'PAGE_USER')
    // The user page is refused, so only the unwired entry survives.
    expect(projected.routes).toHaveLength(1)
    expect(projected.unwired).toEqual(['PAGE_NOT_WIRED'])
  })

  it('projects nothing when the caller holds no permission at all', () => {
    const menus: MenuNode[] = [
      {
        id: '1',
        permission_code: 'MENU_SYSTEM',
        permission_name: '系统管理',
        resource_type: 'MENU',
        resource_code: 'MENU_SYSTEM',
        parent_id: null,
        sort_order: 10,
      },
    ]
    const projected = projectMenu(menus, () => false)
    expect(projected.groups).toHaveLength(0)
    expect(projected.routes).toHaveLength(0)
  })
})
