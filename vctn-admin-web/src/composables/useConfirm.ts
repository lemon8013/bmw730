/**
 * Destructive action confirmation.
 *
 * Every irreversible or wide-impact action goes through here so the wording and
 * the "type to confirm" strength are consistent, and so no page can skip the
 * confirmation by accident.
 */

import { ElMessage, ElMessageBox, type Action } from 'element-plus'

/** Options for one confirmation. */
export interface ConfirmOptions {
  /** Dialog title. */
  title: string
  /** Body text. */
  message: string
  /** Label of the confirming button. */
  confirmText?: string
  /** Label of the cancelling button. */
  cancelText?: string
  /** Render the confirm button in the danger style. */
  danger?: boolean
  /**
   * Require the operator to retype this text before the action is allowed.
   * Used for the actions that cannot be undone.
   */
  requireTypedText?: string
}

/** Ask for confirmation; resolves `true` only when confirmed. */
export async function confirmAction(options: ConfirmOptions): Promise<boolean> {
  try {
    const typed =
      options.requireTypedText === undefined
        ? undefined
        : {
            inputPattern: new RegExp(`^${options.requireTypedText}$`),
            inputErrorMessage: `请输入 ${options.requireTypedText} 以确认`,
            inputPlaceholder: options.requireTypedText,
          }
    await ElMessageBox.confirm(options.message, options.title, {
      confirmButtonText: options.confirmText ?? '确认',
      cancelButtonText: options.cancelText ?? '取消',
      type: options.danger === true ? 'warning' : 'info',
      draggable: true,
      ...(typed ?? {}),
    })
    return true
  } catch (action) {
    // Element Plus rejects with 'cancel' / 'close'; neither is an error.
    void (action as Action)
    return false
  }
}

/** Show a success toast. */
export function notifySuccess(message: string): void {
  ElMessage.success(message)
}

/** Show an informational toast. */
export function notifyInfo(message: string): void {
  ElMessage.info(message)
}

/** Show a warning toast. */
export function notifyWarning(message: string): void {
  ElMessage.warning(message)
}

/** Show a failure toast. */
export function notifyError(message: string): void {
  ElMessage.error(message)
}

/** The object returned by {@link useConfirm}. */
export interface ConfirmResult {
  confirm: (options: ConfirmOptions) => Promise<boolean>
  success: (message: string) => void
  info: (message: string) => void
  warning: (message: string) => void
  failure: (message: string) => void
}

/** Convenience wrapper around the confirmation and the toasts. */
export function useConfirm(): ConfirmResult {
  return {
    confirm: confirmAction,
    success: notifySuccess,
    info: notifyInfo,
    warning: notifyWarning,
    failure: notifyError,
  }
}
