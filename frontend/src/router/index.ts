import { createRouter, createWebHistory } from 'vue-router'
import { getAdminToken } from '../lib/auth'
import AdminDashboardView from '../views/AdminDashboardView.vue'
import AdminLoginView from '../views/AdminLoginView.vue'
import GroupSiteView from '../views/GroupSiteView.vue'
import LinkExpiredView from '../views/LinkExpiredView.vue'

const router = createRouter({
  history: createWebHistory('/yiyin/'),
  routes: [
    { path: '/', redirect: '/admin' },
    { path: '/admin', name: 'admin-login', component: AdminLoginView, meta: { guestOnly: true } },
    { path: '/admin/dashboard', name: 'admin-dashboard', component: AdminDashboardView, meta: { requiresAuth: true } },
    { path: '/expired', name: 'expired', component: LinkExpiredView },
    { path: '/:groupId', name: 'group-site', component: GroupSiteView },
  ],
})

router.beforeEach((to) => {
  const hasToken = Boolean(getAdminToken())
  if (to.meta.requiresAuth && !hasToken) {
    return { name: 'admin-login' }
  }
  if (to.meta.guestOnly && hasToken) {
    return { name: 'admin-dashboard' }
  }
  return true
})

export default router
