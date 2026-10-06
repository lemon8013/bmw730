import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import ArticlePage from '@/pages/ArticlePage.vue'
import AuthorPage from '@/pages/AuthorPage.vue'
import AuthorsPage from '@/pages/AuthorsPage.vue'
import CategoryPage from '@/pages/CategoryPage.vue'
import HomePage from '@/pages/HomePage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import MinePage from '@/pages/MinePage.vue'
import SearchPage from '@/pages/SearchPage.vue'

/**
 * The public blog: feed, category, article, author directory, search and the
 * author centre.
 *
 * `/login` sits outside `AppLayout` on purpose — the form should not carry the
 * article navigation, and the layout's account area already links to it.
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
      { path: '', name: 'home', component: HomePage, meta: { title: '首页' } },
      {
        path: 'category/:code',
        name: 'category',
        component: CategoryPage,
        meta: { title: '分类' },
      },
      {
        path: 'article/:id',
        name: 'article',
        component: ArticlePage,
        meta: { title: '文章' },
      },
      { path: 'authors', name: 'authors', component: AuthorsPage, meta: { title: '作者' } },
      {
        path: 'author/:id',
        name: 'author',
        component: AuthorPage,
        meta: { title: '作者主页' },
      },
      { path: 'search', name: 'search', component: SearchPage, meta: { title: '搜索' } },
      { path: 'mine', name: 'mine', component: MinePage, meta: { title: '作者中心' } },
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
    document.title = (typeof title === 'string' && title !== '' ? `${title} · ` : '') + 'VCTN Blog'
  })
  return router
}
