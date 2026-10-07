/**
 * Turn the backend menu tree into router records.
 *
 * The backend sends **one** menu tree per administrator and it contains every
 * site: the management platform's `MENU_*` / `PAGE_*` nodes as well as this
 * console's `MENU_OPS_CONSOLE` / `PAGE_OPS_*` nodes. This projection keeps only
 * this console's branch — the management platform renders the complement — so
 * an operator never sees a menu entry that would take them out of the console.
 *
 * Only permission codes present in `OPS_PAGE_TABLE` become routes; an ops code
 * with no local implementation is reported to the caller instead of being
 * silently dropped, and it is never turned into a dynamic import.
 */

import type { RouteRecordRaw } from 'vue-router'

import { isOpsMenuCode, OPS_MENU_ROOT } from '@/constants/permissions'
import { resolvePage, unwiredPage, type PageDefinition } from '@/router/route-table'
import type { MenuNode } from '@/types/auth'

/** A menu root with the pages underneath it. */
export interface MenuGroup {
  /** Stable key: the menu permission code. */
  key: string
  title: string
  icon: string
  sortOrder: number
  pages: MenuEntry[]
}

/** One routable page inside a menu group. */
export interface MenuEntry {
  page: PageDefinition
  permissionCode: string
  title: string
  icon: string
  sortOrder: number
}

/** The result of projecting the backend menu onto the local route table. */
export interface ProjectedMenu {
  groups: MenuGroup[]
  routes: RouteRecordRaw[]
  /** Ops permission codes the backend offered that this build does not implement. */
  unwired: string[]
}

function bySortOrder(left: { sortOrder: number; title: string }, right: { sortOrder: number; title: string }): number {
  if (left.sortOrder !== right.sortOrder) {
    return left.sortOrder - right.sortOrder
  }
  return left.title.localeCompare(right.title, 'zh-Hans-CN')
}

/**
 * Project the menu nodes onto local routes.
 *
 * @param menus     Menu nodes as returned by `/admin/auth/permissions`.
 * @param canAccess Predicate deciding whether the caller holds a permission.
 */
export function projectMenu(
  menus: readonly MenuNode[],
  canAccess: (permissionCode: string) => boolean,
): ProjectedMenu {
  // The console's own branch only. Everything else is another frontend's menu.
  const granted = menus.filter((node) => isOpsMenuCode(node.permission_code) && canAccess(node.permission_code))

  const roots = granted
    .filter((node) => node.resource_type === 'MENU')
    .sort((left, right) =>
      bySortOrder(
        { sortOrder: left.sort_order, title: left.permission_name },
        { sortOrder: right.sort_order, title: right.permission_name },
      ),
    )

  const childrenOf = new Map<string, MenuNode[]>()
  for (const node of granted) {
    if (node.resource_type !== 'PAGE' || node.parent_id === null || node.parent_id === undefined) {
      continue
    }
    const bucket = childrenOf.get(node.parent_id)
    if (bucket === undefined) {
      childrenOf.set(node.parent_id, [node])
    } else {
      bucket.push(node)
    }
  }

  const groups: MenuGroup[] = []
  const routes: RouteRecordRaw[] = []
  const unwired: string[] = []
  const seenPaths = new Set<string>()

  for (const root of roots) {
    const entries: MenuEntry[] = []
    const children = (childrenOf.get(root.id) ?? []).sort((left, right) =>
      bySortOrder(
        { sortOrder: left.sort_order, title: left.permission_name },
        { sortOrder: right.sort_order, title: right.permission_name },
      ),
    )

    for (const child of children) {
      const page = resolvePage(child.permission_code)
      if (page === null) {
        unwired.push(child.permission_code)
        entries.push({
          page: { ...unwiredPage, path: `${unwiredPage.path}/${child.permission_code}` },
          permissionCode: child.permission_code,
          title: child.permission_name,
          icon: unwiredPage.icon,
          sortOrder: child.sort_order,
        })
        continue
      }
      if (seenPaths.has(page.path)) {
        continue
      }
      seenPaths.add(page.path)
      entries.push({
        page,
        permissionCode: child.permission_code,
        title: page.title,
        icon: page.icon,
        sortOrder: child.sort_order,
      })
    }

    if (entries.length === 0) {
      continue
    }

    groups.push({
      key: root.permission_code,
      title: root.permission_name,
      icon: root.permission_code === OPS_MENU_ROOT ? 'Monitor' : 'Menu',
      sortOrder: root.sort_order,
      pages: entries,
    })

    for (const entry of entries) {
      routes.push({
        path: entry.page.path,
        name: entry.page.name,
        component: entry.page.component,
        meta: {
          title: entry.title,
          icon: entry.icon,
          permission: entry.permissionCode,
        },
      })
    }
  }

  groups.sort((left, right) =>
    bySortOrder({ sortOrder: left.sortOrder, title: left.title }, { sortOrder: right.sortOrder, title: right.title }),
  )

  return { groups, routes, unwired }
}

/**
 * The permission code of the page the console opens after a sign-in.
 *
 * The menus are sorted on the backend, so "the first allowed route" would work
 * as well — until someone reorders the menu and every operator lands somewhere
 * else after a password change. Naming the landing page here makes it a fact
 * about this build rather than a fact about a seed row.
 */
const LANDING_PAGE_CODE = 'PAGE_OPS_REPORT'

/**
 * The page the caller lands on after signing in.
 *
 * The preferred page wins only when the caller actually holds it; otherwise
 * the first allowed route is used, so an operator without report access still
 * gets a usable console instead of a 403.
 */
export function firstAllowedPath(projected: ProjectedMenu): string {
  const preferred = projected.routes.find(
    (record) => record.meta?.permission === LANDING_PAGE_CODE,
  )
  return preferred?.path ?? projected.routes[0]?.path ?? '/403'
}
