<template>
  <el-popover
    placement="bottom-end"
    :width="360"
    trigger="click"
    @show="onShow"
  >
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="notification-bell">
        <el-icon :size="20"><Bell /></el-icon>
      </el-badge>
    </template>

    <div class="notification-popover">
      <div class="notification-popover-header">
        <span class="notification-popover-title">Notifications</span>
        <el-button
          v-if="unreadCount > 0"
          type="primary"
          link
          size="small"
          @click="handleMarkAllRead"
        >
          Mark all read
        </el-button>
      </div>
      <div class="notification-popover-body">
        <div
          v-for="item in notificationList"
          :key="item.id"
          class="notification-item"
          :class="{ 'is-unread': !item.is_read }"
          @click="handleMarkRead(item)"
        >
          <div class="notification-dot" v-if="!item.is_read" />
          <div class="notification-content">
            <div class="notification-title">{{ item.title }}</div>
            <div class="notification-message text-truncate">{{ item.content }}</div>
            <div class="notification-time">{{ formatTime(item.created_at) }}</div>
          </div>
        </div>
        <el-empty v-if="notificationList.length === 0" description="No notifications" :image-size="60" />
      </div>
      <div class="notification-popover-footer">
        <router-link to="/notifications">
          <el-button type="primary" link size="small">View all</el-button>
        </router-link>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { ElMessage } from 'element-plus'

const notificationStore = useNotificationStore()
const notificationList = ref([])

const unreadCount = ref(0)

onMounted(() => {
  loadUnreadCount()
})

async function loadUnreadCount() {
  try {
    await notificationStore.fetchUnreadCount()
    unreadCount.value = notificationStore.unreadCount
  } catch {
    // silent
  }
}

async function onShow() {
  try {
    await notificationStore.fetchNotifications({ limit: 5 })
    notificationList.value = notificationStore.notifications.slice(0, 5)
  } catch {
    // silent
  }
}

async function handleMarkRead(item) {
  if (item.is_read) return
  try {
    await notificationStore.markAsRead(item.id)
    item.is_read = true
    unreadCount.value = notificationStore.unreadCount
  } catch {
    ElMessage.error('Operation failed')
  }
}

async function handleMarkAllRead() {
  try {
    await notificationStore.markAllRead()
    notificationList.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
    ElMessage.success('All marked as read')
  } catch {
    ElMessage.error('Operation failed')
  }
}

function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return Math.floor(diff / 60000) + 'min ago'
  if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago'
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.notification-bell {
  cursor: pointer;
  line-height: 1;
}

.notification-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid #f2f3f5;
  margin-bottom: 4px;
}

.notification-popover-title {
  font-weight: 600;
  font-size: 14px;
}

.notification-popover-body {
  max-height: 360px;
  overflow-y: auto;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 0;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f5f7fa;
  margin: 0 -8px;
  padding: 10px 8px;
  border-radius: 4px;
}

.notification-item.is-unread {
  background: #f0f5ff;
  margin: 0 -8px;
  padding: 10px 8px;
  border-radius: 4px;
}

.notification-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409EFF;
  flex-shrink: 0;
  margin-top: 6px;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 2px;
}

.notification-message {
  font-size: 12px;
  color: #909399;
  margin-bottom: 2px;
}

.notification-time {
  font-size: 11px;
  color: #c0c4cc;
}

.notification-popover-footer {
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid #f2f3f5;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
