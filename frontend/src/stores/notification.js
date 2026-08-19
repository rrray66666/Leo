import { defineStore } from 'pinia'
import { notificationApi } from '@/api'

export const useNotificationStore = defineStore('notification', {
  state: () => ({
    notifications: [],
    unreadCount: 0,
    total: 0
  }),

  actions: {
    async fetchNotifications(params = {}) {
      try {
        const res = await notificationApi.list(params)
        this.notifications = res.data?.items || res.data || []
        this.total = res.data?.total || res.total || 0
        return res
      } catch (error) {
        throw error
      }
    },

    async fetchUnreadCount() {
      try {
        const res = await notificationApi.unreadCount()
        this.unreadCount = res.data?.count || res.count || 0
        return this.unreadCount
      } catch (error) {
        throw error
      }
    },

    async markAsRead(id) {
      try {
        const res = await notificationApi.markRead(id)
        this.unreadCount = Math.max(0, this.unreadCount - 1)
        const notif = this.notifications.find(n => n.id === id)
        if (notif) notif.is_read = true
        return res
      } catch (error) {
        throw error
      }
    },

    async markAllRead() {
      try {
        const res = await notificationApi.markAllRead()
        this.unreadCount = 0
        this.notifications.forEach(n => { n.is_read = true })
        return res
      } catch (error) {
        throw error
      }
    }
  }
})
