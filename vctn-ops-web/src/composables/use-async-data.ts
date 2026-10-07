/** Minimal async data holder shared by every page. */

import { ref, watch, type Ref } from 'vue'

/** State of one async load. */
export interface AsyncDataState<T> {
  readonly data: Ref<T | null>
  readonly loading: Ref<boolean>
  readonly failed: Ref<boolean>
  readonly error: Ref<string | null>
  readonly reload: () => Promise<void>
}

function describeError(failure: unknown): string {
  if (failure instanceof Error && failure.message.trim() !== '') {
    return failure.message
  }
  return '加载失败，请稍后重试'
}

/**
 * Run `loader` immediately and expose loading / failed / error state.
 *
 * `reload` re-runs the loader; a stale response from a previous run is dropped,
 * which matters on pages whose filters change without a remount.
 */
export function useAsyncData<T>(loader: () => Promise<T>): AsyncDataState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const failed = ref(false)
  const error = ref<string | null>(null)
  let sequence = 0

  async function reload(): Promise<void> {
    const run = ++sequence
    loading.value = true
    failed.value = false
    error.value = null
    try {
      const result = await loader()
      if (run !== sequence) {
        return
      }
      data.value = result
    } catch (failure: unknown) {
      if (run !== sequence) {
        return
      }
      failed.value = true
      error.value = describeError(failure)
    } finally {
      if (run === sequence) {
        loading.value = false
      }
    }
  }

  void reload()

  return { data, loading, failed, error, reload }
}

/**
 * Re-run `loader` whenever `source` changes.
 *
 * List pages bind this to their filter object, so a filter change reloads
 * without a remount and without an imperative watcher in every component.
 */
export function useAsyncDataWatch<T>(
  loader: () => Promise<T>,
  source: () => unknown,
): AsyncDataState<T> {
  const state = useAsyncData(loader)
  watch(source, () => {
    void state.reload()
  })
  return state
}
