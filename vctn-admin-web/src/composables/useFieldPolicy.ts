/**
 * Field level control for one form, resolved once and shared by every field.
 *
 * A page declares which permission governs the resource and then asks for the
 * mode of a field. No page re-implements the rule, and the local deny list is
 * always applied on top of whatever the backend declared.
 */

import { computed, type ComputedRef } from 'vue'

import { usePermissionStore } from '@/stores/permission'
import type { FieldMode } from '@/types/enums'

/** The object returned by {@link useFieldPolicy}. */
export interface FieldPolicyResult {
  /** Mode declared for one field. */
  modeOf: (field: string) => FieldMode
  /** Whether the field must not be rendered. */
  isHidden: (field: string) => boolean
  /** Whether the field is visible but not editable. */
  isReadOnly: (field: string) => boolean
  /** Whether the field may be edited. */
  isEditable: (field: string) => boolean
  /** The whole policy, for templates that iterate over fields. */
  modes: ComputedRef<Record<string, FieldMode>>
}

/** Bind a form to the field policy of one permission code. */
export function useFieldPolicy(permissionCode: string): FieldPolicyResult {
  const store = usePermissionStore()

  const modes = computed<Record<string, FieldMode>>(() => store.fieldModes(permissionCode))

  function modeOf(field: string): FieldMode {
    return modes.value[field] ?? 'VISIBLE'
  }

  return {
    modeOf,
    isHidden: (field) => modeOf(field) === 'HIDDEN',
    isReadOnly: (field) => modeOf(field) === 'READ_ONLY',
    isEditable: (field) => modeOf(field) === 'EDITABLE' || modeOf(field) === 'VISIBLE',
    modes,
  }
}
