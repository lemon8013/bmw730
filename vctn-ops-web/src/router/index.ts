/**
 * Router construction.
 *
 * Only the shell routes are declared statically. Every business page is added
 * by {@link installDynamicRoutes} once the backend has answered
 * `/admin/auth/permissions`, so the menu, the routes and the guards always come
 * from one source: the permission codes the backend granted.
 *
 * The detail pages (a single host, service or endpoint) are declared statically
 * because the backend menu carries no node for them: they guard on the same
 * permission code as the list they belong to.
 */

import { createRouter, createWebHistory, type RouteRecordRaw, type Router } from 'vue-router'

import { SHELL_ROUTE_NAME } from '@/router/dynamic-routes'
import { registerGuards } from '@/router/guards'

export {
  SHELL_ROUTE_NAME,
  installDynamicRoutes,
  uninstallDynamicRoutes,
} from '@/router/dynamic-routes'

const shellChildren = (): RouteRecordRaw[] => [
  {
    path: 'ops/hosts/:hostId',
    name: 'ops-host-detail',
    component: () => import('@/pages/HostDetailPage.vue'),
    meta: { title: '主机详情', permission: 'PAGE_OPS_HOST' },
  },
  {
    path: 'ops/services/:serviceId',
    name: 'ops-service-detail',
    component: () => import('@/pages/ServiceDetailPage.vue'),
    meta: { title: '服务详情', permission: 'PAGE_OPS_SERVICE' },
  },
  {
    path: 'ops/apis/:endpointId',
    name: 'ops-api-detail',
    component: () => import('@/pages/ApiDetailPage.vue'),
    meta: { title: '端点详情', permission: 'PAGE_OPS_API' },
  },
]

const routes: RouteRecordRaw[] = [
  {
    // Outside the shell on purpose: the login form must not carry the console
    // chrome, and it is the one page a signed-out visitor is allowed to reach.
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    name: SHELL_ROUTE_NAME,
    component: () => import('@/layouts/OpsLayout.vue'),
    children: shellChildren(),
  },
  {
    path: '/403',
    name: 'error-403',
    component: () => import('@/pages/errors/ForbiddenPage.vue'),
    meta: { title: '无权访问' },
  },
  {
    path: '/500',
    name: 'error-500',
    component: () => import('@/pages/errors/ServerErrorPage.vue'),
    meta: { title: '服务异常' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'error-404',
    component: () => import('@/pages/errors/NotFoundPage.vue'),
    meta: { title: '页面不存在' },
  },
]

/** Create the application router. */
export function createAppRouter(): Router {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes,
    scrollBehavior: () => ({ top: 0 }),
  })
  registerGuards(router)
  return router
}
