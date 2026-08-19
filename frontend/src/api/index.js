import request from './request'

// ==================== Authentication ====================
export const authApi = {
  login(data) {
    return request.post('/auth/login', data)
  },
  register(data) {
    return request.post('/auth/register', data)
  },
  refresh() {
    return request.post('/auth/refresh')
  },
  getMe() {
    return request.get('/auth/me')
  }
}

// ==================== Customers ====================
export const customerApi = {
  create(data) {
    return request.post('/customers', data)
  },
  list(params) {
    return request.get('/customers', { params })
  },
  detail(id) {
    return request.get(`/customers/${id}`)
  },
  update(id, data) {
    return request.put(`/customers/${id}`, data)
  },
  delete(id) {
    return request.delete(`/customers/${id}`)
  },
  advanceStage(id, data) {
    return request.put(`/customers/${id}/stage`, data)
  },
  updateStatus(id, data) {
    return request.put(`/customers/${id}/status`, data)
  },
  assign(id, data) {
    return request.put(`/customers/${id}/assign`, data)
  },
  rollback(id, data) {
    return request.put(`/customers/${id}/rollback`, data)
  },
  getTimeline(id) {
    return request.get(`/customers/${id}/timeline`)
  },
  advancedSearch(params) {
    return request.get('/customers/advanced-search', { params })
  },
  batchAssign(data) {
    return request.post('/customers/batch/assign', data)
  },
  batchStatus(data) {
    return request.post('/customers/batch/status', data)
  },
  batchDelete(data) {
    return request.post('/customers/batch/delete', data)
  },
  importExcel(data) {
    return request.post('/customers/import', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  exportExcel(params) {
    return request.get('/customers/export', { params, responseType: 'blob' })
  },
  downloadTemplate() {
    return request.get('/customers/export-template', { responseType: 'blob' })
  }
}

// ==================== Contracts ====================
export const contractApi = {
  create(customerId, data) {
    return request.post(`/customers/${customerId}/contract`, data)
  },
  getByCustomer(customerId) {
    return request.get(`/customers/${customerId}/contract`)
  },
  update(id, data) {
    return request.put(`/contracts/${id}`, data)
  },
  replaceFile(id, data) {
    return request.put(`/contracts/${id}/file`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete(id) {
    return request.delete(`/contracts/${id}`)
  }
}

// ==================== Tasks ====================
export const taskApi = {
  create(customerId, data) {
    return request.post(`/customers/${customerId}/tasks`, data)
  },
  list(params) {
    return request.get(`/customers/${params.customer_id}/tasks`, { params })
  },
  detail(id) {
    return request.get(`/tasks/${id}`)
  },
  update(id, data) {
    return request.put(`/tasks/${id}`, data)
  },
  updateStatus(id, data) {
    return request.patch(`/tasks/${id}/status`, data)
  },
  updateAssignee(id, data) {
    return request.patch(`/tasks/${id}/assignee`, data)
  },
  delete(id) {
    return request.delete(`/tasks/${id}`)
  }
}

// ==================== Documents ====================
export const documentApi = {
  create(customerId, data) {
    return request.post(`/customers/${customerId}/documents`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list(params) {
    return request.get(`/customers/${params.customer_id}/documents`, { params })
  },
  detail(id) {
    return request.get(`/documents/${id}`)
  },
  download(id) {
    return request.get(`/documents/${id}/download`, { responseType: 'blob' })
  },
  update(id, data) {
    return request.put(`/documents/${id}`, data)
  },
  replaceFile(id, data) {
    return request.put(`/documents/${id}/file`, data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  delete(id) {
    return request.delete(`/documents/${id}`)
  }
}

// ==================== Communication Records ====================
export const communicationApi = {
  create(customerId, data) {
    return request.post(`/customers/${customerId}/communications`, data)
  },
  list(params) {
    return request.get(`/customers/${params.customer_id}/communications`, { params })
  },
  update(id, data) {
    return request.put(`/communications/${id}`, data)
  },
  delete(id) {
    return request.delete(`/communications/${id}`)
  }
}

// ==================== Payments ====================
export const paymentApi = {
  create(customerId, data) {
    return request.post(`/customers/${customerId}/payments`, data)
  },
  list(params) {
    return request.get(`/customers/${params.customer_id}/payments`, { params })
  },
  update(id, data) {
    return request.put(`/payments/${id}`, data)
  },
  delete(id) {
    return request.delete(`/payments/${id}`)
  }
}

// ==================== Board/Kanban ====================
export const boardApi = {
  getKanban(params) {
    return request.get('/board/kanban', { params })
  },
  getAlerts() {
    return request.get('/board/alerts')
  }
}

// ==================== Dashboard ====================
export const dashboardApi = {
  getStats() {
    return request.get('/dashboard/stats')
  },
  getFunnel() {
    return request.get('/dashboard/funnel')
  },
  getSales() {
    return request.get('/dashboard/sales')
  },
  getPayments(params) {
    return request.get('/dashboard/payment-trend', { params })
  }
}

// ==================== Users ====================
export const userApi = {
  create(data) {
    return request.post('/users', data)
  },
  list(params) {
    return request.get('/users', { params })
  },
  update(id, data) {
    return request.put(`/users/${id}`, data)
  },
  resetPassword(id, data) {
    return request.put(`/users/${id}/password`, data)
  },
  getMe() {
    return request.get('/users/me')
  },
  updateMe(data) {
    return request.put('/users/me', data)
  },
  updateMyPassword(data) {
    return request.put('/users/me/password', data)
  }
}

// ==================== Notifications ====================
export const notificationApi = {
  list(params) {
    return request.get('/notifications', { params })
  },
  unreadCount() {
    return request.get('/notifications/unread-count')
  },
  markRead(id) {
    return request.put(`/notifications/${id}/read`)
  },
  markAllRead() {
    return request.put('/notifications/read-all')
  }
}

// ==================== Follow-ups ====================
export const followUpApi = {
  create(data) {
    const { customer_id, ...rest } = data
    return request.post(`/customers/${customer_id}/follow-ups`, null, { params: rest })
  },
  list(params) {
    return request.get(`/customers/${params.customer_id}/follow-ups`, { params })
  },
  update(id, data) {
    return request.put(`/follow-ups/${id}`, null, { params: data })
  },
  markDone(id) {
    return request.put(`/follow-ups/${id}/done`)
  },
  delete(id) {
    return request.delete(`/follow-ups/${id}`)
  },
  todayList() {
    return request.get('/follow-ups/today')
  }
}

// ==================== Audit Logs ====================
export const auditLogApi = {
  list(params) {
    return request.get('/audit-logs', { params })
  },
  customerLogs(customerId) {
    return request.get(`/customers/${customerId}/audit-logs`)
  }
}

// ==================== Data Dictionary ====================
export const dictApi = {
  getIndustries() {
    return request.get('/dict/industries')
  },
  getRegions() {
    return request.get('/dict/regions')
  },
  getChannels() {
    return request.get('/dict/channels')
  },
  getCategories() {
    return request.get('/dict/categories')
  },
  updateIndustries(data) {
    return request.put('/dict/industries', data)
  },
  updateRegions(data) {
    return request.put('/dict/regions', data)
  },
  updateChannels(data) {
    return request.put('/dict/channels', data)
  },
  updateCategories(data) {
    return request.put('/dict/categories', data)
  }
}

// ==================== Search ====================
export const searchApi = {
  globalSearch(params) {
    return request.get('/search/global', { params })
  }
}
