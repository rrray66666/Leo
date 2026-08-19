import { defineStore } from 'pinia'
import { authApi, userApi } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null'),
    permissions: []
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.userInfo?.role === 'admin',
    role: (state) => state.userInfo?.role || '',
    userName: (state) => state.userInfo?.name || state.userInfo?.email || '',
    avatar: (state) => state.userInfo?.avatar || ''
  },

  actions: {
    async login(credentials) {
      try {
        const res = await authApi.login(credentials)
        const { access_token, user } = res.data || res
        this.token = access_token
        this.userInfo = user
        localStorage.setItem('token', access_token)
        localStorage.setItem('userInfo', JSON.stringify(user))
        return res
      } catch (error) {
        throw error
      }
    },

    async register(userData) {
      try {
        const res = await authApi.register(userData)
        const { access_token, user } = res.data || res
        this.token = access_token
        this.userInfo = user
        localStorage.setItem('token', access_token)
        localStorage.setItem('userInfo', JSON.stringify(user))
        return res
      } catch (error) {
        throw error
      }
    },

    logout() {
      this.token = ''
      this.userInfo = null
      this.permissions = []
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
    },

    async fetchUserInfo() {
      try {
        const res = await authApi.getMe()
        this.userInfo = res.data || res
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        return this.userInfo
      } catch (error) {
        this.logout()
        throw error
      }
    },

    async updateProfile(data) {
      try {
        const res = await userApi.updateMe(data)
        this.userInfo = { ...this.userInfo, ...data }
        localStorage.setItem('userInfo', JSON.stringify(this.userInfo))
        return res
      } catch (error) {
        throw error
      }
    },

    async changePassword(data) {
      try {
        const res = await userApi.updateMyPassword(data)
        return res
      } catch (error) {
        throw error
      }
    }
  }
})
