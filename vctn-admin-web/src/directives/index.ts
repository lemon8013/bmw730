/** Global directives. */

import type { App } from 'vue'

import { fieldDirective } from '@/directives/field'
import { permissionDirective } from '@/directives/permission'

/** Register every application directive. */
export function registerDirectives(app: App): void {
  app.directive('permission', permissionDirective)
  app.directive('field', fieldDirective)
}
