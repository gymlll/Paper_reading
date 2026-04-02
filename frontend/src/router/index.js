import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/DashboardView.vue'),
  },
  {
    path: '/papers',
    name: 'PaperLibrary',
    component: () => import('../views/PaperLibraryView.vue'),
  },
  {
    path: '/papers/:id',
    name: 'PaperDetail',
    component: () => import('../views/PaperDetailView.vue'),
    props: true,
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/UploadView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
