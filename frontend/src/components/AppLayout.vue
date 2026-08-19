<template>
  <div class="app-layout">
    <!-- Top navigation bar -->
    <header class="navbar">
      <div class="navbar-left">
        <div class="logo" @click="router.push('/')">
          <el-icon :size="24"><Management /></el-icon>
          <span class="logo-text">CRM System</span>
        </div>
        <el-breadcrumb separator="/" class="breadcrumb">
          <el-breadcrumb-item :to="{ path: '/' }">Home</el-breadcrumb-item>
          <el-breadcrumb-item v-if="currentTitle">{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      <div class="navbar-right">
        <GlobalSearch />
        <NotificationBell />
        <el-dropdown trigger="click" @command="handleUserCommand">
          <span class="user-dropdown">
            <el-avatar :size="32" :icon="UserFilled" />
            <span class="user-name">{{ userStore.userName }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><Avatar /></el-icon>Profile
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>Logout
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="app-body">
      <!-- Sidebar -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <el-menu
          :default-active="activeMenu"
          :collapse="sidebarCollapsed"
          router
          class="sidebar-menu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/kanban">
            <el-icon><Grid /></el-icon>
            <span>Kanban</span>
          </el-menu-item>
          <el-menu-item index="/customer/list">
            <el-icon><List /></el-icon>
            <span>Customer List</span>
          </el-menu-item>
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <span>Dashboard</span>
          </el-menu-item>
          <el-menu-item index="/follow-ups">
            <el-icon><AlarmClock /></el-icon>
            <span>Today's Follow-ups</span>
          </el-menu-item>
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <span>Notifications</span>
          </el-menu-item>
          <el-menu-item index="/import-export">
            <el-icon><Upload /></el-icon>
            <span>Import/Export</span>
          </el-menu-item>
          <el-menu-item index="/audit-logs">
            <el-icon><Tickets /></el-icon>
            <span>Audit Logs</span>
          </el-menu-item>

          <!-- Admin Menu -->
          <template v-if="userStore.isAdmin">
            <el-sub-menu index="admin">
              <template #title>
                <el-icon><Setting /></el-icon>
                <span>System</span>
              </template>
              <el-menu-item index="/users">User Management</el-menu-item>
              <el-menu-item index="/dict">Data Dictionary</el-menu-item>
            </el-sub-menu>
          </template>
        </el-menu>

        <div class="sidebar-collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon>
            <Fold v-if="!sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
        </div>
      </aside>

      <!-- Main Content Area -->
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox, ElMessage } from 'element-plus'
import GlobalSearch from '@/components/GlobalSearch.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import { UserFilled } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const sidebarCollapsed = ref(false)

const activeMenu = computed(() => route.path)

const currentTitle = computed(() => route.meta?.title || '')

function handleUserCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    ElMessageBox.confirm('Are you sure you want to logout?', 'Confirm', {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      type: 'warning'
    }).then(() => {
      userStore.logout()
      router.push('/login')
      ElMessage.success('Logged out successfully')
    }).catch(() => {})
  }
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Top Navigation */
.navbar {
  height: var(--navbar-height, 56px);
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #409EFF;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.breadcrumb {
  font-size: 13px;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.user-dropdown:hover {
  background: #f5f7fa;
}

.user-name {
  font-size: 14px;
  color: #303133;
}

/* Main Body */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width, 220px);
  background: #304156;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
  position: relative;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width, 64px);
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: var(--sidebar-width, 220px);
}

.sidebar-collapse-btn {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #bfcbd9;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  transition: color 0.2s;
}

.sidebar-collapse-btn:hover {
  color: #409EFF;
}

/* Main Content */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: #f0f2f5;
}
</style>
