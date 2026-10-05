/**
 * Dynamic route installation.
 *
 * Business pages do not exist in the static route table: they are contributed
 * from the menu the backend returned, so the menu, the routes and the guard all
 * read the same permission projection.
 *
 * Kept in its own module (rather than beside `createAppRouter`) because both the
 * router factory and the navigation guard need it; a shared module avoids a
 * circular import between those two.
 */

import type { RouteRecordRaw, Router } from 'vue-router'

/** Name of the shell route that hosts every business page. */
export const SHELL_ROUTE_NAME = 'shell'

/** Route names contributed by the last install. */
let contributed: string[] = []

/** The exact array the current contribution came from, for cheap no-op checks. */
let contributedFrom: readonly RouteRecordRaw[] | null = null

/** Whether these records have already been installed. */
export function dynamicRoutesMatch(records: readonly RouteRecordRaw[]): boolean {
  return contributedFrom === records
}

/**
 * Replace the dynamically contributed routes.
 *
 * Called after every permission load and cleared on sign out. Removing the old
 * records first keeps a re-login from accumulating stale pages. Passing the same
 * array twice is a no-op, so a guard may call it on every navigation.
 */
export function installDynamicRoutes(router: Router, records: readonly RouteRecordRaw[]): void {
  if (contributedFrom === records) {
    return
  }
  uninstallDynamicRoutes(router)
  for (const record of records) {
    router.addRoute(SHELL_ROUTE_NAME, { ...record, path: record.path.replace(/^\//, '') })
  }
  contributedFrom = records
  contributed = records
    .map((record) => (typeof record.name === 'string' ? record.name : null))
    .filter((name): name is string => name !== null)
}

/** Remove every route contributed by the last permission load. */
export function uninstallDynamicRoutes(router: Router): void {
  for (const name of contributed) {
    if (router.hasRoute(name)) {
      router.removeRoute(name)
    }
  }
  contributed = []
  contributedFrom = null
}
