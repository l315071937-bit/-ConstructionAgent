import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/projects', component: () => import('../views/WorkspaceEntryView.vue') },
    { path: '/projects/:id', component: () => import('../views/ProjectChatView.vue') },
    { path: '/', redirect: '/projects' }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.token) return '/login'
  if (to.path === '/login' && auth.token) return '/projects'
})

export default router
