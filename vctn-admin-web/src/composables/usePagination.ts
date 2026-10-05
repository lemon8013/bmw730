/**
 * Pagination state bound to the backend's frozen parameters.
 *
 * The backend paginates with `page` (1-based) and `page_size`; nothing here
 * introduces an offset or a cursor.
 */

import { computed, ref, type Ref } from 'vue'

import type { Page, PageQuery } from '@/types/api'

/** Default page size used across the console. */
export const DEFAULT_PAGE_SIZE = 20

/** The page sizes offered in the table footer. */
export const PAGE_SIZES: readonly number[] = [10, 20, 50, 100]

/**
 * Largest `page_size` the API accepts.
 *
 * Mirrors `MAX_PAGE_SIZE` in `vctn-api/app/shared/pagination/params.py`. Asking
 * for more makes the server reject the request with 422, so any "load every
 * option" call must clamp to this value.
 */
export const MAX_PAGE_SIZE = 200

/** The object returned by {@link usePagination}. */
export interface PaginationResult {
  page: Ref<number>
  pageSize: Ref<number>
  total: Ref<number>
  query: Ref<PageQuery>
  totalPages: Ref<number>
  setTotal: (value: number) => void
  applyPage: (next: Page<unknown>) => void
  changePage: (nextPage: number) => void
  changePageSize: (nextSize: number) => void
  reset: () => void
}

/** Create the pagination state of one list page. */
export function usePagination(initialSize: number = DEFAULT_PAGE_SIZE): PaginationResult {
  const page = ref(1)
  const pageSize = ref(initialSize)
  const total = ref(0)

  const query = computed<PageQuery>(() => ({
    page: page.value,
    page_size: pageSize.value,
  }))

  const totalPages = computed(() =>
    pageSize.value > 0 ? Math.max(1, Math.ceil(total.value / pageSize.value)) : 1,
  )

  function setTotal(value: number): void {
    total.value = Math.max(0, value)
  }

  function applyPage(next: Page<unknown>): void {
    total.value = Math.max(0, next.total ?? 0)
  }

  function changePage(nextPage: number): void {
    page.value = Math.max(1, nextPage)
  }

  function changePageSize(nextSize: number): void {
    pageSize.value = Math.max(1, nextSize)
    page.value = 1
  }

  function reset(): void {
    page.value = 1
    total.value = 0
  }

  return {
    page,
    pageSize,
    total,
    query,
    totalPages,
    setTotal,
    applyPage,
    changePage,
    changePageSize,
    reset,
  }
}
