import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import CategoryPage from '@/pages/CategoryPage.vue'
import HomePage from '@/pages/HomePage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import PopularPage from '@/pages/PopularPage.vue'
import RecentPage from '@/pages/RecentPage.vue'
import SearchPage from '@/pages/SearchPage.vue'
import ToolWorkbenchPage from '@/pages/ToolWorkbenchPage.vue'

/**
 * The tool portal per `aicoding/spec/04-Tools平台Spec/03-工具前台.md`:
 * home, category, search, popular, recent and the tool workbench.
 *
 * `/login` sits outside `AppLayout` on purpose: the sign-in form should not
 * carry the catalogue navigation, and the layout's user menu already covers the
 * way in.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: HomePage,
        meta: { title: '首页' },
      },
      {
        path: 'category/:slug',
        name: 'category',
        component: CategoryPage,
        meta: { title: '分类' },
      },
      {
        path: 'search',
        name: 'search',
        component: SearchPage,
        meta: { title: '搜索' },
      },
      {
        path: 'popular',
        name: 'popular',
        component: PopularPage,
        meta: { title: '热门' },
      },
      {
        path: 'recent',
        name: 'recent',
        component: RecentPage,
        meta: { title: '最近使用' },
      },
      {
        path: 'tool/:slug',
        name: 'tool',
        component: ToolWorkbenchPage,
        meta: { title: '工具' },
      },
    ],
  },
]

export function createAppRouter() {
  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes,
  })
  router.afterEach((to) => {
    const title = to.meta.title
    document.title =
      (typeof title === 'string' && title !== '' ? `${title} · ` : '') + 'VCTN Tools'
  })
  return router
}
