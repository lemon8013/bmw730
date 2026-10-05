/**
 * Turn the backend menu tree into router records.
 *
 * The backend sends a flat list of `MenuNode`s: `MENU` roots and `PAGE`
 * children, linked by `parent_id`. Only permission codes present in
 * {@link PAGE_TABLE} become routes; a code with no local implementation is
 * reported to the caller instead of being silently dropped, and it is never
 * turned into a dynamic import.
 */

import type { RouteRecordRaw } from 'vue-router'

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
  /** Permission codes the backend offered that this build does not implement. */
  unwired: string[]
}

const MENU_ICONS: Readonly<Record<string, string>> = {
  MENU_DASHBOARD: 'Odometer',
  MENU_SYSTEM: 'Setting',
  MENU_LOG: 'Document',
  MENU_TOOL: 'Suitcase',
  MENU_ANALYTICS: 'DataAnalysis',
  MENU_BLOG: 'Notebook',
  MENU_GROWTH: 'TrendCharts',
  MENU_OPS: 'Tools',
}

function bySortOrder<T extends { sortOrder: number; key?: string; title: string }>(
  left: T,
  right: T,
): number {
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
  const granted = menus.filter((node) => canAccess(node.permission_code))
  const roots = granted
    .filter((node) => node.resource_type === 'MENU')
    .sort((left, right) => bySortOrder(
      { sortOrder: left.sort_order, title: left.permission_name },
      { sortOrder: right.sort_order, title: right.permission_name },
    ))

  const childrenOf = new Map<string, MenuNode[]>()
  for (const node of granted) {
    if (node.resource_type !== 'PAGE' || !node.parent_id) {
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
      icon: MENU_ICONS[root.permission_code] ?? 'Menu',
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

  groups.sort((left, right) => bySortOrder(
    { sortOrder: left.sortOrder, title: left.title },
    { sortOrder: right.sortOrder, title: right.title },
  ))

  return { groups, routes, unwired }
}

/** The first page the caller is allowed to open, used as the landing route. */
export function firstAllowedPath(projected: ProjectedMenu): string {
  return projected.routes[0]?.path ?? '/403'
}
