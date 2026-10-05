/**
 * Clipboard access with a graceful fallback.
 *
 * The asynchronous Clipboard API needs a secure context; when it is unavailable
 * the legacy selection path is used instead of failing silently.
 */

import { ref } from 'vue'

import { notifySuccess } from '@/composables/useConfirm'

/** The object returned by {@link useClipboard}. */
export interface ClipboardResult {
  copied: ReturnType<typeof ref<boolean>>
  copy: (text: string, successMessage?: string) => Promise<boolean>
}

function legacyCopy(text: string): boolean {
  const area = document.createElement('textarea')
  area.value = text
  area.setAttribute('readonly', '')
  area.style.position = 'fixed'
  area.style.opacity = '0'
  document.body.appendChild(area)
  area.select()
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  document.body.removeChild(area)
  return ok
}

/** Copy text to the clipboard. */
export function useClipboard(): ClipboardResult {
  const copied = ref(false)

  async function copy(text: string, successMessage?: string): Promise<boolean> {
    let ok = false
    if (typeof navigator !== 'undefined' && navigator.clipboard !== undefined) {
      try {
        await navigator.clipboard.writeText(text)
        ok = true
      } catch {
        ok = legacyCopy(text)
      }
    } else {
      ok = legacyCopy(text)
    }
    copied.value = ok
    if (ok && successMessage !== undefined) {
      notifySuccess(successMessage)
    }
    return ok
  }

  return { copied, copy }
}
