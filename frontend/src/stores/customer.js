import { defineStore } from 'pinia'
import { customerApi, boardApi } from '@/api'

export const useCustomerStore = defineStore('customer', {
  state: () => ({
    kanbanData: [],
    currentCustomer: null,
    customerList: [],
    total: 0,
    loading: false
  }),

  getters: {
    kanbanByStage: (state) => {
      const stages = [
        { id: 1, name: 'Lead' },
        { id: 2, name: 'Consult' },
        { id: 3, name: 'Contract' },
        { id: 4, name: 'Requirements' },
        { id: 5, name: 'Service' },
        { id: 6, name: 'Delivery' },
        { id: 7, name: 'Payment' },
        { id: 8, name: 'Completed' }
      ]
      return stages.map(stage => {
        const column = state.kanbanData.find(k => k.stage === stage.id)
        return {
          ...stage,
          customers: column?.customers || [],
          count: column?.count || 0
        }
      })
    }
  },

  actions: {
    async fetchKanban(filters = {}) {
      this.loading = true
      try {
        const res = await boardApi.getKanban(filters)
        this.kanbanData = res.data || res
        return this.kanbanData
      } catch (error) {
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCustomers(params = {}) {
      this.loading = true
      try {
        const res = await customerApi.list(params)
        this.customerList = res.data?.items || res.data || []
        this.total = res.data?.total || res.total || 0
        return res
      } catch (error) {
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchCustomerDetail(id) {
      this.loading = true
      try {
        const res = await customerApi.detail(id)
        const data = res.data || res
        this.currentCustomer = { ...data, stage: data.current_stage }
        return this.currentCustomer
      } catch (error) {
        throw error
      } finally {
        this.loading = false
      }
    },

    async advanceStage(id, data) {
      try {
        const res = await customerApi.advanceStage(id, data)
        await this.fetchCustomerDetail(id)
        return res
      } catch (error) {
        throw error
      }
    },

    async updateCustomer(id, data) {
      try {
        const res = await customerApi.update(id, data)
        this.currentCustomer = { ...this.currentCustomer, ...data }
        return res
      } catch (error) {
        throw error
      }
    },

    async createCustomer(data) {
      try {
        const res = await customerApi.create(data)
        return res
      } catch (error) {
        throw error
      }
    },

    async deleteCustomer(id) {
      try {
        const res = await customerApi.delete(id)
        return res
      } catch (error) {
        throw error
      }
    },

    async batchAssign(data) {
      try {
        const res = await customerApi.batchAssign(data)
        return res
      } catch (error) {
        throw error
      }
    },

    async batchStatus(data) {
      try {
        const res = await customerApi.batchStatus(data)
        return res
      } catch (error) {
        throw error
      }
    },

    async batchDelete(data) {
      try {
        const res = await customerApi.batchDelete(data)
        return res
      } catch (error) {
        throw error
      }
    }
  }
})
