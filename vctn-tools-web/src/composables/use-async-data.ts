/** Minimal async data holder shared by every page. */

import { onMounted, ref, type Ref } from 'vue'

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
 * Run `loader` once on mount and expose loading / failed / error state.
 * `reload` re-runs the loader; failures never throw into the caller.
 */
export function useAsyncData<T>(loader: () => Promise<T>): AsyncDataState<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const failed = ref(false)
  const error = ref<string | null>(null)

  async function reload(): Promise<void> {
    loading.value = true
    failed.value = false
    error.value = null
    try {
      data.value = await loader()
    } catch (failure: unknown) {
      failed.value = true
      error.value = describeError(failure)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void reload()
  })

  return { data, loading, failed, error, reload }
}
