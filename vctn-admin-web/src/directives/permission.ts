/**
 * `v-permission` — remove an element when the caller lacks a permission.
 *
 * Usage:
 *   v-permission="'USER_CREATE'"
 *   v-permission:any="['USER_EDIT', 'USER_DELETE']"
 *   v-permission:all="['ROLE_ASSIGN', 'ROLE_VIEW']"
 *
 * The element is detached from the DOM rather than hidden with CSS, so a user
 * cannot reveal it by editing styles. This is a presentation decision only:
 * the backend still refuses the call.
 */

import type { Directive, DirectiveBinding } from 'vue'

import { usePermissionStore } from '@/stores/permission'

type PermissionValue = string | readonly string[]

function isGranted(binding: DirectiveBinding<PermissionValue>): boolean {
  const store = usePermissionStore()
  const value = binding.value
  if (typeof value === 'string') {
    return store.has(value)
  }
  if (Array.isArray(value)) {
    return binding.arg === 'all' ? store.all(value) : store.any(value)
  }
  // A malformed binding must not silently reveal the element.
  return false
}

function removeElement(element: HTMLElement): void {
  element.parentNode?.removeChild(element)
}

export const permissionDirective: Directive<HTMLElement, PermissionValue> = {
  mounted(element, binding) {
    if (binding.value === undefined || binding.value === null) {
      removeElement(element)
      return
    }
    if (!isGranted(binding)) {
      removeElement(element)
    }
  },
}
