<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Audit Logs</h2>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-select v-model="filters.action" placeholder="Action Type" clearable @change="loadData">
        <el-option label="Create" value="create" />
        <el-option label="Update" value="update" />
        <el-option label="Delete" value="delete" />
        <el-option label="Stage Advance" value="advance_stage" />
      </el-select>
      <el-select v-model="filters.resource_type" placeholder="Object Type" clearable @change="loadData">
        <el-option label="Customer" value="customer" />
        <el-option label="Contract" value="contract" />
        <el-option label="Task" value="task" />
        <el-option label="Payment" value="payment" />
      </el-select>
      <el-input
        v-model="filters.operator_name"
        placeholder="Operator"
        clearable
        style="width:150px"
        @change="loadData"
        @clear="loadData"
      />
      <el-date-picker
        v-model="filters.date_range"
        type="daterange"
        range-separator="to"
        start-placeholder="Start Date"
        end-placeholder="End Date"
        value-format="YYYY-MM-DD"
        @change="loadData"
      />
    </div>

    <el-table :data="logs" v-loading="loading" stripe>
      <el-table-column prop="created_at" label="Time" width="160" />
      <el-table-column prop="operator_name" label="Operator" width="120" />
      <el-table-column prop="action" label="Action" width="100">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)" size="small">
            {{ actionMap[row.action] || row.action }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="Object" width="100">
        <template #default="{ row }">
          {{ resourceMap[row.resource_type] || row.resource_type }}
        </template>
      </el-table-column>
      <el-table-column prop="resource_id" label="Object ID" width="100" />
      <el-table-column prop="description" label="Description" min-width="200" />
      <el-table-column label="Changes" min-width="200">
        <template #default="{ row }">
          <div v-if="row.changes" class="changes-content">
            <div v-for="(change, key) in row.changes" :key="key" class="change-item">
              <span class="change-key">{{ key }}:</span>
              <span class="change-old">{{ change.old ?? '-' }}</span>
              <el-icon :size="12"><ArrowRight /></el-icon>
              <span class="change-new">{{ change.new ?? '-' }}</span>
            </div>
          </div>
          <span v-else class="text-secondary">-</span>
        </template>
      </el-table-column>
    </el-table>

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
import { auditLogApi } from '@/api'
import { ArrowRight } from '@element-plus/icons-vue'

const loading = ref(false)
const logs = ref([])
const total = ref(0)

const filters = reactive({
  action: '',
  resource_type: '',
  operator_name: '',
  date_range: null
})

const pagination = reactive({ page: 1, pageSize: 20 })

const actionMap = {
  create: 'Created',
  update: 'Updated',
  delete: 'Deleted',
  advance_stage: 'Stage Advanced'
}

const resourceMap = {
  customer: 'Customer',
  contract: 'Contract',
  task: 'Task',
  payment: 'Payment',
  communication: 'Communication',
  document: 'Document'
}

function actionType(action) {
  const map = { create: 'success', update: 'primary', delete: 'danger', advance_stage: 'warning' }
  return map[action] || 'info'
}

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const params = { page: pagination.page, page_size: pagination.pageSize }
    if (filters.action) params.action = filters.action
    if (filters.resource_type) params.object_type = filters.resource_type
    if (filters.operator_name) params.operator_name = filters.operator_name
    if (filters.date_range) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }
    const res = await auditLogApi.list(params)
    logs.value = res.data?.items || res.data || []
    total.value = res.data?.total || res.total || 0
  } catch {
    logs.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.changes-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.change-key {
  font-weight: 600;
  color: #303133;
  min-width: 60px;
}

.change-old {
  color: #f56c6c;
  text-decoration: line-through;
}

.change-new {
  color: #67C23A;
  font-weight: 500;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.text-secondary {
  color: #909399;
}
</style>
