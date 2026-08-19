import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
request.interceptors.response.use(
  (response) => {
    const { data } = response
    if (data.code === 0 || data.code === undefined) {
      return data
    }
    ElMessage.error(data.message || 'Request failed')
    return Promise.reject(new Error(data.message || 'Request failed'))
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          // A 401 on the login/register endpoint means wrong credentials,
          // not an expired session - show the backend message and stop.
          if (error.config?.url?.includes('/auth/')) {
            const detail = typeof data?.detail === 'string' ? data.detail : 'Invalid email or password'
            ElMessage.error(detail)
            return Promise.reject(error)
          }
          localStorage.removeItem('token')
          localStorage.removeItem('userInfo')
          ElMessage.error('Login expired, please login again')
          router.push('/login')
          break
        case 403:
          ElMessage.error('No permission to perform this action')
          break
        case 404:
          ElMessage.error('Requested resource not found')
          break
        case 422:
          ElMessage.error(data.detail?.[0]?.msg || 'Invalid request parameters')
          break
        case 500:
          ElMessage.error('Internal server error')
          break
        default:
          ElMessage.error(data?.message || `Request failed (${status})`)
      }
    } else if (error.message?.includes('timeout')) {
      ElMessage.error('Request timeout, please check network')
    } else {
      ElMessage.error('Network error, please check connection')
    }
    return Promise.reject(error)
  }
)

export default request
