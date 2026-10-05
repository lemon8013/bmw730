/**
 * `v-field` — apply the field policy declared for a permission code.
 *
 * Usage:
 *   v-field="{ permission: 'USER_VIEW', field: 'email' }"
 *
 * `HIDDEN` detaches the element; `READ_ONLY` disables form controls inside it
 * and blocks pointer input. The policy comes from the permission store, which
 * merges the backend's declaration with the local deny list, so password and
 * MFA material can never be rendered.
 */

import type { Directive, DirectiveBinding } from 'vue'

import { usePermissionStore } from '@/stores/permission'
import type { FieldMode } from '@/types/enums'

/** The binding accepted by `v-field`. */
export interface FieldBinding {
  permission: string
  field: string
  /** Optional fallback when no policy is declared for the field. */
  fallback?: FieldMode
}

function readMode(binding: DirectiveBinding<FieldBinding>): FieldMode {
  const value = binding.value
  if (value === undefined || value === null || typeof value !== 'object') {
    return 'HIDDEN'
  }
  const store = usePermissionStore()
  const modes = store.fieldModes(value.permission)
  return modes[value.field] ?? value.fallback ?? 'VISIBLE'
}

function applyReadOnly(element: HTMLElement): void {
  element.classList.add('is-field-readonly')
  for (const control of element.querySelectorAll<
    HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | HTMLButtonElement
  >('input, textarea, select, button')) {
    control.disabled = true
  }
}

export const fieldDirective: Directive<HTMLElement, FieldBinding> = {
  mounted(element, binding) {
    const mode = readMode(binding)
    if (mode === 'HIDDEN') {
      element.parentNode?.removeChild(element)
      return
    }
    if (mode === 'READ_ONLY') {
      applyReadOnly(element)
    }
  },
}
