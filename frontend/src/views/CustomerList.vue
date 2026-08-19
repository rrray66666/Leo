<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Customer List</h2>
      <div class="page-header-actions">
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">New Customer</el-button>
        <el-button :icon="Download" @click="handleExport">Export</el-button>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <el-select v-model="filters.stage" placeholder="Filter by stage" clearable>
        <el-option v-for="s in stageOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="filters.sales_id" placeholder="Filter by sales" clearable filterable>
        <el-option v-for="s in salesList" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-select v-model="filters.region" placeholder="Filter by region" clearable>
        <el-option v-for="r in regionList" :key="r" :label="r" :value="r" />
      </el-select>
      <el-select v-model="filters.alert_level" placeholder="Alert Level" clearable>
        <el-option label="Normal" value="normal" />
        <el-option label="Warning" value="warning" />
        <el-option label="Overdue" value="danger" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="Search by name/contact..."
        clearable
        :prefix-icon="Search"
      />
      <el-button type="primary" :icon="Search" @click="applyFilters">Filter</el-button>
      <el-button @click="resetFilters">Reset</el-button>
    </div>

    <!-- Batch operations bar -->
    <div v-if="selectedIds.length > 0" class="batch-bar">
      <span>Selected {{ selectedIds.length }} items</span>
      <el-button size="small" @click="showBatchAssign = true">Batch Transfer</el-button>
      <el-button size="small" @click="showBatchStatus = true">Batch Update Status</el-button>
      <el-popconfirm title="Confirm batch delete?" @confirm="handleBatchDelete">
        <template #reference>
          <el-button size="small" type="danger">Batch Delete</el-button>
        </template>
      </el-popconfirm>
      <el-button size="small" text @click="handleDeselect">Deselect</el-button>
    </div>

    <!-- Customer table -->
    <el-table
      ref="tableRef"
      :data="customerList"
      v-loading="customerStore.loading"
      stripe
      @selection-change="selectedIds = $event.map(i => i.id)"
      @row-dblclick="(row) => $router.push(`/customer/${row.id}`)"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="name" label="Customer Name" min-width="140" sortable>
        <template #default="{ row }">
          <el-link type="primary" @click="$router.push(`/customer/${row.id}`)">{{ row.name }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="contact_person" label="Contact" width="110" />
      <el-table-column prop="phone" label="Phone" width="120" />
      <el-table-column prop="region" label="Region" width="100" />
      <el-table-column prop="stage" label="Stage" width="100">
        <template #default="{ row }">
          <StageTag :stage="row.current_stage" size="small" />
        </template>
      </el-table-column>
      <el-table-column prop="sales_name" label="Sales Rep" width="100" />
      <el-table-column prop="contract_amount" label="Contract Amount" width="120" sortable>
        <template #default="{ row }">
          <span>{{ formatAmount(row.contract_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="stay_days" label="Stay(d)" width="90" sortable>
        <template #default="{ row }">
          <span :class="row.alert_level === 'danger' ? 'text-danger' : row.alert_level === 'warning' ? 'text-warning' : ''">
            {{ row.stay_days || 0 }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created At" width="160" sortable />
      <el-table-column label="Actions" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/customer/${row.id}`)">View</el-button>
          <el-button link type="primary" @click="handleEdit(row)">Edit</el-button>
          <el-popconfirm title="Confirm delete?" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">Delete</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="customerStore.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="loadData"
      />
    </div>

    <!-- Create customer dialog -->
    <el-dialog v-model="showCreateDialog" title="New Customer" width="600px">
      <el-form :model="createForm" label-width="100px" ref="createFormRef" :rules="createRules">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Customer Name" prop="name">
              <el-input v-model="createForm.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Contact Person" prop="contact_person">
              <el-input v-model="createForm.contact_person" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Phone" prop="phone">
              <el-input v-model="createForm.phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Email (optional)">
              <el-input v-model="createForm.email" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Company (optional)">
              <el-input v-model="createForm.company" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Region (optional)">
              <el-input v-model="createForm.region" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="WeChat (optional)">
              <el-input v-model="createForm.wechat" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Source Channel (optional)">
              <el-input v-model="createForm.source_channel" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button>
      </template>
    </el-dialog>

    <!-- Batch Transfer dialog -->
    <el-dialog v-model="showBatchAssign" title="Batch Transfer" width="400px">
      <el-form label-width="80px">
        <el-form-item label="Transfer to">
          <el-select v-model="batchAssignTarget" placeholder="Select sales" filterable style="width:100%">
            <el-option v-for="s in salesList" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchAssign = false">Cancel</el-button>
        <el-button type="primary" @click="confirmBatchAssign">Confirm Transfer</el-button>
      </template>
    </el-dialog>

    <!-- Batch Update Status dialog -->
    <el-dialog v-model="showBatchStatus" title="Batch Update Status" width="400px">
      <el-form label-width="80px">
        <el-form-item label="Target Status">
          <el-select v-model="batchStatusTarget" placeholder="Select status" style="width:100%">
            <el-option label="Active" value="active" />
            <el-option label="Lost" value="lost" />
            <el-option label="Completed" value="completed" />
            <el-option label="Terminated" value="terminated" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchStatus = false">Cancel</el-button>
        <el-button type="primary" @click="confirmBatchStatus">Confirm Update</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useCustomerStore } from '@/stores/customer'
import { userApi, dictApi, customerApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Plus, Download, Search } from '@element-plus/icons-vue'
import StageTag from '@/components/StageTag.vue'

const customerStore = useCustomerStore()
const customerList = ref([])
const selectedIds = ref([])
const creating = ref(false)
const showCreateDialog = ref(false)
const showBatchAssign = ref(false)
const showBatchStatus = ref(false)
const batchAssignTarget = ref(null)
const batchStatusTarget = ref(null)
const createFormRef = ref(null)
const tableRef = ref(null)

const stageOptions = [
  { value: 1, label: 'Lead' },
  { value: 2, label: 'Consult' },
  { value: 3, label: 'Contract' },
  { value: 4, label: 'Requirements' },
  { value: 5, label: 'Service' },
  { value: 6, label: 'Delivery' },
  { value: 7, label: 'Payment' },
  { value: 8, label: 'Completed' }
]

const filters = reactive({
  stage: '',
  sales_id: '',
  region: '',
  alert_level: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const salesList = ref([])
const regionList = ref([])

const createForm = reactive({
  name: '', contact_person: '', phone: '', email: '',
  company: '', region: '', wechat: '', source_channel: ''
})

const createRules = {
  name: [{ required: true, message: 'Please enter customer name', trigger: 'blur' }],
  contact_person: [{ required: true, message: 'Please enter contact person', trigger: 'blur' }],
  phone: [{ required: true, message: 'Please enter phone number', trigger: 'blur' }]
}

onMounted(async () => {
  await loadData()
  loadFilterOptions()
})

async function loadFilterOptions() {
  try {
    const res = await userApi.list()
    salesList.value = (res.data?.items || res.data || []).filter(u => u.role === 'sales')
  } catch {
    salesList.value = []
  }
  try {
    const res = await dictApi.getRegions()
    const data = res.data
    regionList.value = Array.isArray(data)
      ? data.map(r => (typeof r === 'string' ? r : r.name)).filter(Boolean)
      : []
  } catch {
    regionList.value = []
  }
}

async function loadData() {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ...filters
  }
  Object.keys(params).forEach(k => { if (!params[k]) delete params[k] })
  try {
    const res = await customerStore.fetchCustomers(params)
    customerList.value = customerStore.customerList
  } catch {
    customerList.value = []
  }
}

function formatAmount(val) {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (isNaN(num)) return '-'
  return '¥' + num.toLocaleString()
}

function applyFilters() {
  pagination.page = 1
  loadData()
}

function resetFilters() {
  Object.assign(filters, { stage: '', sales_id: '', region: '', alert_level: '', keyword: '' })
  pagination.page = 1
  loadData()
}

function handleDeselect() {
  selectedIds.value = []
  tableRef.value?.clearSelection()
}

async function handleCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    await customerStore.createCustomer(createForm)
    ElMessage.success('Created successfully')
    showCreateDialog.value = false
    Object.assign(createForm, { name: '', contact_person: '', phone: '', email: '', company: '', region: '', wechat: '', source_channel: '' })
    await loadData()
  } catch (error) {
    ElMessage.error(typeof error.response?.data?.detail === 'string' ? error.response.data.detail : (error.response?.data?.message || 'Failed to create'))
  } finally {
    creating.value = false
  }
}

function handleEdit(row) {
  ElMessage.info('Edit feature is available on the customer detail page')
}

async function handleDelete(id) {
  try {
    await customerStore.deleteCustomer(id)
    ElMessage.success('Deleted successfully')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Failed to delete')
  }
}

async function confirmBatchAssign() {
  if (!batchAssignTarget.value) {
    ElMessage.warning('Please select a sales rep')
    return
  }
  try {
    await customerStore.batchAssign({ customer_ids: selectedIds.value, new_sales_id: batchAssignTarget.value })
    ElMessage.success('Batch transfer successful')
    showBatchAssign.value = false
    selectedIds.value = []
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Transfer failed')
  }
}

async function confirmBatchStatus() {
  if (!batchStatusTarget.value) {
    ElMessage.warning('Please select a target status')
    return
  }
  try {
    await customerStore.batchStatus({ customer_ids: selectedIds.value, status: batchStatusTarget.value })
    ElMessage.success('Batch update successful')
    showBatchStatus.value = false
    selectedIds.value = []
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Update failed')
  }
}

async function handleBatchDelete() {
  try {
    await customerStore.batchDelete(selectedIds.value)
    ElMessage.success('Batch delete successful')
    selectedIds.value = []
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Failed to delete')
  }
}

async function handleExport() {
  try {
    const params = {}
    if (filters.stage) params.stage = filters.stage
    if (filters.sales_id) params.sales_id = filters.sales_id
    if (filters.region) params.region = filters.region
    const res = await customerApi.exportExcel(params)
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `customers_${new Date().toLocaleDateString('en-US')}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('Export successful')
  } catch {
    ElMessage.error('Export failed')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
}

.page-header-actions {
  display: flex;
  gap: 8px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: #ecf5ff;
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
