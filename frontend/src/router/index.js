import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    redirect: '/kanban',
    children: [
      {
        path: 'kanban',
        name: 'Kanban',
        component: () => import('@/views/Kanban.vue'),
        meta: { title: 'Kanban', requiresAuth: true }
      },
      {
        path: 'customer/list',
        name: 'CustomerList',
        component: () => import('@/views/CustomerList.vue'),
        meta: { title: 'Customer List', requiresAuth: true }
      },
      {
        path: 'customer/:id',
        name: 'CustomerDetail',
        component: () => import('@/views/CustomerDetail.vue'),
        meta: { title: 'Customer Detail', requiresAuth: true }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: 'Dashboard', requiresAuth: true }
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('@/views/UserManage.vue'),
        meta: { title: 'User Management', requiresAuth: true, roles: ['admin'] }
      },
      {
        path: 'notifications',
        name: 'NotificationList',
        component: () => import('@/views/NotificationList.vue'),
        meta: { title: 'Notifications', requiresAuth: true }
      },
      {
        path: 'follow-ups',
        name: 'FollowUpList',
        component: () => import('@/views/FollowUpList.vue'),
        meta: { title: 'Today\'s Follow-ups', requiresAuth: true }
      },
      {
        path: 'audit-logs',
        name: 'AuditLog',
        component: () => import('@/views/AuditLog.vue'),
        meta: { title: 'Audit Logs', requiresAuth: true }
      },
      {
        path: 'dict',
        name: 'DictManage',
        component: () => import('@/views/DictManage.vue'),
        meta: { title: 'Data Dictionary', requiresAuth: true, roles: ['admin'] }
      },
      {
        path: 'import-export',
        name: 'ImportExport',
        component: () => import('@/views/ImportExport.vue'),
        meta: { title: 'Import/Export', requiresAuth: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: 'Profile', requiresAuth: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Global route guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
    return
  }

  if (to.path === '/login' && token) {
    next('/')
    return
  }

  if (to.meta.roles) {
    const userInfoStr = localStorage.getItem('userInfo')
    if (userInfoStr) {
      try {
        const userInfo = JSON.parse(userInfoStr)
        if (!to.meta.roles.includes(userInfo.role)) {
          next('/kanban')
          return
        }
      } catch {
        next('/login')
        return
      }
    }
  }

  next()
})

export default router
