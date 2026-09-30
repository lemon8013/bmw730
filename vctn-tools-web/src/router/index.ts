import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import ScaffoldView from '@/pages/ScaffoldView.vue'

/**
 * Phase 0 holds a single scaffold route so that the router can be verified.
 * Tool pages, search and category routes are added in later phases.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'scaffold',
    component: ScaffoldView,
    meta: { title: 'Phase 0 scaffold' },
  },
]

export function createAppRouter() {
  return createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes,
  })
}
