<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Notifications</h2>
      <el-button v-if="unreadCount > 0" type="primary" @click="handleMarkAllRead">Mark All as Read</el-button>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-select v-model="filters.type" placeholder="Notification Type" clearable @change="loadData">
        <el-option label="System" value="system" />
        <el-option label="Stage Change" value="stage_change" />
        <el-option label="Alert" value="alert" />
        <el-option label="Follow-up" value="follow_up" />
      </el-select>
    </div>

    <div class="notification-list" v-loading="loading">
      <div
        v-for="item in notifications"
        :key="item.id"
        class="notification-card"
        :class="{ 'is-unread': !item.is_read }"
        @click="handleMarkRead(item)"
      >
        <div class="notification-indicator">
          <div v-if="!item.is_read" class="unread-dot" />
        </div>
        <div class="notification-main">
          <div class="notification-header">
            <span class="notification-title">{{ item.title }}</span>
            <div class="notification-meta">
              <el-tag v-if="item.type" size="small" effect="plain">
                {{ typeMap[item.type] || item.type }}
              </el-tag>
              <span class="notification-time">{{ item.created_at }}</span>
            </div>
          </div>
          <div class="notification-body">{{ item.content }}</div>
          <div v-if="item.customer_name" class="notification-footer">
            <el-link type="primary" @click.stop="$router.push(`/customer/${item.customer_id}`)">
              View Details →
            </el-link>
          </div>
        </div>
      </div>
      <el-empty v-if="notifications.length === 0" description="No notifications" />
    </div>

    <!-- Pagination -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @change="loadData"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { ElMessage } from 'element-plus'

const notificationStore = useNotificationStore()

const notifications = ref([])
const total = ref(0)
const unreadCount = ref(0)
const loading = ref(false)

const filters = reactive({ type: '' })
const pagination = reactive({ page: 1, pageSize: 20 })

const typeMap = {
  system: 'System',
  stage_change: 'Stage Change',
  alert: 'Alert',
  follow_up: 'Follow-up'
}

onMounted(async () => {
  await Promise.all([loadData(), loadUnreadCount()])
})

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (filters.type) params.type = filters.type
    const res = await notificationStore.fetchNotifications(params)
    notifications.value = notificationStore.notifications
    total.value = notificationStore.total
  } catch {
    notifications.value = []
  } finally {
    loading.value = false
  }
}

async function loadUnreadCount() {
  try {
    await notificationStore.fetchUnreadCount()
    unreadCount.value = notificationStore.unreadCount
  } catch { /* silent */ }
}

async function handleMarkRead(item) {
  if (item.is_read) return
  await notificationStore.markAsRead(item.id)
  item.is_read = true
  unreadCount.value = notificationStore.unreadCount
}

async function handleMarkAllRead() {
  try {
    await notificationStore.markAllRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
    ElMessage.success('All marked as read')
  } catch {
    ElMessage.error('Operation failed')
  }
}
</script>

<style scoped>
.notification-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-card {
  display: flex;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.notification-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.notification-card.is-unread {
  background: #f0f5ff;
}

.notification-indicator {
  width: 16px;
  flex-shrink: 0;
  padding-top: 4px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409EFF;
}

.notification-main {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.notification-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.notification-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.notification-time {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.notification-body {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.notification-footer {
  margin-top: 8px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
