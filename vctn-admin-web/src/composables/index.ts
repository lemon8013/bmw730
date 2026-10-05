/** Reusable composition functions. */

export {
  isEmptyValue,
  useAsyncData,
  type AsyncDataOptions,
  type AsyncDataResult,
  type AsyncStatus,
} from '@/composables/useAsyncData'
export { useClipboard, type ClipboardResult } from '@/composables/useClipboard'
export { useConfirm, type ConfirmOptions, type ConfirmResult } from '@/composables/useConfirm'
export { useFieldPolicy, type FieldPolicyResult } from '@/composables/useFieldPolicy'
export {
  DEFAULT_PAGE_SIZE,
  MAX_PAGE_SIZE,
  PAGE_SIZES,
  usePagination,
  type PaginationResult,
} from '@/composables/usePagination'
