import { AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import ElementPlus, { ElButton } from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createApp } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { ApiEnvelopeError, apiBaseUrl, httpClient } from '@/api/client'
import { routes } from '@/router'
import { useAppStore } from '@/stores/app'

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

describe('admin web scaffold', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    while (adapterRestorers.length > 0) {
      adapterRestorers.pop()?.()
    }
  })

  it('initialises the pinia store', () => {
    const store = useAppStore()
    expect(store.applicationName).toBe('VCTN Admin')
    expect(store.apiPrefix).toBe(apiBaseUrl)
  })

  it('resolves the scaffold route', () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    expect(router.resolve('/').matched).toHaveLength(1)
  })

  it('registers element plus on a vue application', () => {
    const app = createApp({ render: () => null })
    app.use(ElementPlus)
    expect(app.component('ElButton')).toBeTruthy()
    expect(ElButton).toBeTruthy()
  })

  it('creates the axios instance with the configured base url', () => {
    expect(httpClient.defaults.baseURL).toBe(apiBaseUrl)
    expect(typeof httpClient.interceptors.request.use).toBe('function')
    expect(typeof httpClient.interceptors.response.use).toBe('function')
  })

  it('attaches trace headers and unwraps a success envelope', async () => {
    const original = httpClient.defaults.adapter
    let captured: InternalAxiosRequestConfig | undefined
    httpClient.defaults.adapter = async (
      config: InternalAxiosRequestConfig,
    ): Promise<AxiosResponse> => {
      captured = config
      return {
        data: { code: 0, message: 'success', data: null },
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

  it('rejects a non-zero envelope code', async () => {
    respondWith({ code: 403001, message: 'permission denied', data: null })
    await expect(httpClient.get('/probe')).rejects.toBeInstanceOf(ApiEnvelopeError)
  })

  it('normalises a transport failure', async () => {
    const original = httpClient.defaults.adapter
    httpClient.defaults.adapter = async (): Promise<AxiosResponse> => {
      throw new Error('connection refused')
    }
    await expect(httpClient.get('/probe')).rejects.toBeInstanceOf(Error)
    httpClient.defaults.adapter = original
  })
})
