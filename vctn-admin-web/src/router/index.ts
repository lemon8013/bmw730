/**
 * Router construction.
 *
 * Only the shell routes are declared statically. Every business page is added
 * by {@link installDynamicRoutes} once the backend has answered
 * `/admin/auth/permissions`, so the menu, the routes and the guards always come
 * from one source: the permission codes the backend granted.
 */

import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
  type Router,
} from 'vue-router'

import { SHELL_ROUTE_NAME } from '@/router/dynamic-routes'
import { registerGuards } from '@/router/guards'

export {
  SHELL_ROUTE_NAME,
  installDynamicRoutes,
  uninstallDynamicRoutes,
} from '@/router/dynamic-routes'

const shellChildren = (): RouteRecordRaw[] => [
  {
    path: 'change-password',
    name: 'change-password',
    component: () => import('@/pages/auth/ChangePasswordPage.vue'),
    meta: { title: '修改密码' },
  },
  {
    path: 'profile',
    name: 'profile',
    component: () => import('@/pages/auth/ProfilePage.vue'),
    meta: { title: '账号信息' },
  },
  {
    // Reached by name from every log page; guarded by TRACE_VIEW.
    path: 'logs/trace/:traceId?',
    name: 'trace-detail',
    component: () => import('@/pages/logs/TracePage.vue'),
    meta: { title: '链路追踪', permission: 'TRACE_VIEW' },
  },
]

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/auth/LoginPage.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    name: SHELL_ROUTE_NAME,
    component: () => import('@/layouts/AdminLayout.vue'),
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
