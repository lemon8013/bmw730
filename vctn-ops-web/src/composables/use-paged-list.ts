/**
 * The list-page contract, in one place.
 *
 * Every list in this console paginates with the backend's `page` / `page_size`
 * and has to render three states — loading, empty, failed. Putting that in one
 * composable means no page can forget the failure branch or leave a spinner
 * running forever.
 */

import { ref, type Ref } from 'vue'

import type { Page } from '@/types/api'
import { renderError } from '@/utils/error'

/** The state returned by {@link usePagedList}. */
export interface PagedList<T> {
  rows: Ref<T[]>
  total: Ref<number>
  page: Ref<number>
  pageSize: Ref<number>
  loading: Ref<boolean>
  failed: Ref<boolean>
  error: Ref<string | null>
  /** Re-run the loader for the current page. */
  reload: () => Promise<void>
  /** Reset to the first page and reload — what a filter change does. */
  search: () => Promise<void>
  changePage: (next: number) => void
  changePageSize: (next: number) => void
}

/**
 * Bind one paginated endpoint to one list page.
 *
 * The loader receives the current page coordinates, so a page never has to
 * thread them through by hand.
 */
export function usePagedList<T>(
  loader: (page: number, pageSize: number) => Promise<Page<T>>,
  initialPageSize = 20,
): PagedList<T> {
  const rows = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(initialPageSize)
  const loading = ref(false)
  const failed = ref(false)
  const error = ref<string | null>(null)
  let sequence = 0

  async function run(): Promise<void> {
    const token = ++sequence
    loading.value = true
    failed.value = false
    error.value = null
    try {
      const result = await loader(page.value, pageSize.value)
      if (token !== sequence) {
        return
      }
      rows.value = result.items ?? []
      total.value = result.total ?? 0
    } catch (caught: unknown) {
      if (token !== sequence) {
        return
      }
      failed.value = true
      error.value = renderError(caught).message
    } finally {
      if (token === sequence) {
        loading.value = false
      }
    }
  }

  function changePage(next: number): void {
    page.value = Math.max(1, next)
    void run()
  }

  function changePageSize(next: number): void {
    pageSize.value = Math.max(1, next)
    page.value = 1
    void run()
  }

  async function search(): Promise<void> {
    page.value = 1
    await run()
  }

  return {
    rows,
    total,
    page,
    pageSize,
    loading,
    failed,
    error,
    reload: run,
    search,
    changePage,
    changePageSize,
  }
}
