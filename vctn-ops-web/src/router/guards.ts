/**
 * Navigation guards.
 *
 * The guard mirrors the backend's decision; it never replaces it. The gates are
 * enforced in this order:
 *
 * 1. the session must exist (otherwise the login page, with a safe return URL);
 * 2. the contributed business routes must be installed before the target is
 *    judged, so a deep link or a refresh reaches its page instead of 404;
 * 3. the target route's `meta.permission` must be held by the caller;
 * 4. a path that matches nothing renders the 404 page.
 */

import type { RouteLocationNormalized, Router } from 'vue-router'

import { installDynamicRoutes } from '@/router/dynamic-routes'
import { APP_TITLE } from '@/router/route-table'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'

/** The only page a signed-out visitor may see. */
const LOGIN_ROUTE = 'login'

/** Error screens that render without a session. */
const GATE_ROUTES: readonly string[] = ['error-403', 'error-500']

/** Name of the catch-all route. */
const NOT_FOUND_ROUTE = 'error-404'

/**
 * Restrict a return URL to an in-application path.
 *
 * An open redirect would let a crafted link move a freshly authenticated
 * operator onto another origin, so anything that is not a plain absolute path
 * inside this application is discarded.
 */
export function safeReturnPath(raw: unknown): string | null {
  if (typeof raw !== 'string' || raw.length === 0) {
    return null
  }
  if (!raw.startsWith('/') || raw.startsWith('//')) {
    return null
  }
  if (raw.includes('\\') || raw.includes('://')) {
    return null
  }
  return raw
}

export function registerGuards(router: Router): void {
  router.beforeEach(async (to: RouteLocationNormalized) => {
    const auth = useAuthStore()
    const permission = usePermissionStore()

    document.title = to.meta.title ? `${String(to.meta.title)} · ${APP_TITLE}` : APP_TITLE

    if (!auth.ready) {
      await auth.restore()
    }

    const routeName = typeof to.name === 'string' ? to.name : ''
    const targetsCatchAll = to.matched.some((record) => record.name === NOT_FOUND_ROUTE)

    // The session is established before anything else, because every other
    // decision depends on it.
    if (!auth.isAuthenticated) {
      if (routeName === LOGIN_ROUTE || GATE_ROUTES.includes(routeName)) {
        return true
      }
      return { name: LOGIN_ROUTE, query: { redirect: to.fullPath }, replace: true }
    }

    // Business routes are contributed from the backend menu, so they must be in
    // place before the target is judged — otherwise the first navigation of a
    // deep link is resolved against the empty table.
    installDynamicRoutes(router, permission.routeRecords)

    if (routeName === LOGIN_ROUTE) {
      return { path: permission.landingPath, replace: true }
    }

    if (targetsCatchAll) {
      const resolved = router.resolve(to.fullPath)
      const matched = resolved.matched.some((record) => record.name !== NOT_FOUND_ROUTE)
      return matched ? { path: to.fullPath, replace: true } : true
    }

    // The bare shell path renders no page of its own.
    if (to.path === '/') {
      return { path: permission.landingPath, replace: true }
    }

    const required = to.meta.permission
    if (typeof required === 'string' && !permission.has(required)) {
      return { name: 'error-403', replace: true }
    }

    return true
  })
}
