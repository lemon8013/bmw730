/**
 * Confirmation for the console's high risk actions.
 *
 * Restarting a job, silencing an alert and deleting a monitored object all
 * change what the platform watches, so none of them happens on a single click.
 * The confirmation is asked here rather than in each page so the wording and
 * the button order stay identical everywhere.
 */

import { ElMessageBox } from 'element-plus'

export interface ConfirmOptions {
  /** Dialog heading. */
  title: string
  /** Sentence explaining what is about to happen. */
  message: string
  /** Label of the confirming button. */
  confirmText?: string
  cancelText?: string
}

/** Ask for confirmation. Resolves `false` when the operator backs out. */
export async function confirmAction(options: ConfirmOptions): Promise<boolean> {
  try {
    await ElMessageBox.confirm(options.message, options.title, {
      type: 'warning',
      confirmButtonText: options.confirmText ?? '确定',
      cancelButtonText: options.cancelText ?? '取消',
      // A click outside must not count as a yes.
      closeOnClickModal: false,
    })
    return true
  } catch {
    return false
  }
}
