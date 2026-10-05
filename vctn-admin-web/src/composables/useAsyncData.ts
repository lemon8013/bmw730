/**
 * One request, with the four states every page needs.
 *
 * Guarantees that a page can never end up as a blank screen or an infinite
 * spinner: `loading`, `error`, `empty` and `ready` are always mutually
 * exclusive and `reload` is always available.
 */

import { computed, ref, shallowRef, type Ref } from 'vue'

import { renderError, type RenderedError } from '@/utils/error'

/** Lifecycle state of one asynchronous load. */
export type AsyncStatus = 'idle' | 'loading' | 'ready' | 'error'

/** Options accepted by {@link useAsyncData}. */
export interface AsyncDataOptions<T> {
  /** Run immediately; otherwise `reload` must be called. */
  immediate?: boolean
  /** Value used before the first successful load. */
  initial?: T
  /** Called when the load fails, after the error state is set. */
  onError?: (error: RenderedError) => void
}

/** The object returned by {@link useAsyncData}. */
export interface AsyncDataResult<T> {
  data: Ref<T>
  status: Ref<AsyncStatus>
  error: Ref<RenderedError | null>
  loading: Ref<boolean>
  ready: Ref<boolean>
  failed: Ref<boolean>
  isEmpty: Ref<boolean>
  reload: () => Promise<void>
}

/** Whether a value should be treated as "no content". */
export function isEmptyValue(value: unknown): boolean {
  if (value === null || value === undefined) {
    return true
  }
  if (Array.isArray(value)) {
    return value.length === 0
  }
  if (typeof value === 'object') {
    const container = value as { items?: unknown; total?: unknown }
    if (Array.isArray(container.items)) {
      return container.items.length === 0
    }
    return Object.keys(value).length === 0
  }
  return false
}

/**
 * Wrap an asynchronous loader in the standard page lifecycle.
 *
 * A stale response can never overwrite a newer one: every run carries a
 * sequence number and only the newest is allowed to commit.
 */
export function useAsyncData<T>(
  loader: () => Promise<T>,
  options: AsyncDataOptions<T> = {},
): AsyncDataResult<T> {
  const data = shallowRef<T>((options.initial ?? null) as T) as Ref<T>
  const status = ref<AsyncStatus>('idle')
  const error = ref<RenderedError | null>(null)
  let sequence = 0

  const loading = computed(() => status.value === 'loading')
  const ready = computed(() => status.value === 'ready')
  const failed = computed(() => status.value === 'error')
  const isEmpty = computed(() => status.value === 'ready' && isEmptyValue(data.value))

  async function reload(): Promise<void> {
    sequence += 1
    const current = sequence
    status.value = 'loading'
    error.value = null
    try {
      const result = await loader()
      if (current !== sequence) {
        return
      }
      data.value = result
      status.value = 'ready'
    } catch (caught) {
      if (current !== sequence) {
        return
      }
      const rendered = renderError(caught)
      error.value = rendered
      status.value = 'error'
      options.onError?.(rendered)
    }
  }

  if (options.immediate !== false) {
    void reload()
  }

  return { data, status, error, loading, ready, failed, isEmpty, reload }
}
