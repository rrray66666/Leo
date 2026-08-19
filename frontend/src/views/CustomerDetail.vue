<template>
  <div class="page-container" v-loading="loading">
    <!-- Header -->
    <div class="detail-header">
      <div class="detail-header-top">
        <div class="detail-title">
          <h2>{{ customer?.name || 'Customer Detail' }}</h2>
          <StageTag v-if="customer?.stage" :stage="customer.stage" size="large" />
          <AlertBadge v-if="customer?.alert_level" :level="customer.alert_level" :days="customer.stay_days" />
        </div>
        <div class="detail-actions">
          <el-button
            v-if="customer?.stage < 8"
            type="primary"
            :icon="Top"
            @click="handleAdvance"
          >
            Advance Stage
          </el-button>
          <el-button :icon="Edit" @click="editMode = !editMode">
            {{ editMode ? 'Cancel Edit' : 'Edit' }}
          </el-button>
          <el-popconfirm title="Confirm deletion of this customer?" @confirm="handleDelete">
            <template #reference>
              <el-button type="danger" :icon="Delete">Delete</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
      <div class="detail-header-info">
        <span><el-icon><Iphone /></el-icon> {{ customer?.phone || '-' }}</span>
        <span><el-icon><ChatDotSquare /></el-icon> {{ customer?.wechat || '-' }}</span>
        <span><el-icon><Message /></el-icon> {{ customer?.email || '-' }}</span>
        <span><el-icon><OfficeBuilding /></el-icon> {{ customer?.company || '-' }}</span>
        <span><el-icon><Location /></el-icon> {{ customer?.region || '-' }}</span>
        <span><el-icon><Avatar /></el-icon> {{ customer?.sales_name || '-' }}</span>
      </div>
    </div>

    <!-- Stage Progress Bar -->
    <div class="detail-section" v-if="customer">
      <h3>Customer Flow</h3>
      <div class="stage-progress">
        <div
          v-for="(s, index) in stageList"
          :key="s.id"
          class="stage-progress-item"
          :class="{
            'completed': s.id < customer.stage,
            'current': s.id === customer.stage,
            'future': s.id > customer.stage
          }"
        >
          <div class="stage-progress-dot" :class="`stage-bg-${s.id}`">
            <el-icon v-if="s.id < customer.stage"><Check /></el-icon>
            <span v-else>{{ index + 1 }}</span>
          </div>
          <div class="stage-progress-label" :class="`stage-color-${s.id}`">{{ s.name }}</div>
          <div v-if="s.id === customer.stage" class="stage-progress-line current-line" />
          <div v-else-if="s.id < customer.stage" class="stage-progress-line completed-line" />
          <div v-else class="stage-progress-line" />
        </div>
      </div>
      <div class="stage-current-info mt-16">
        <span>Current stage has stayed for <strong>{{ customer.stay_days || 0 }}</strong> days</span>
        <span v-if="customer.expected_completion"> | Expected completion: {{ customer.expected_completion }}</span>
      </div>
    </div>

    <!-- Tabs -->
    <div class="detail-section">
      <el-tabs v-model="activeTab">
        <!-- Basic Info -->
        <el-tab-pane label="Basic Info" name="info">
          <el-form
            v-if="customer"
            :model="customer"
            label-width="100px"
            :disabled="!editMode"
            size="default"
          >
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="Customer Name" required>
                  <el-input v-model="customer.name" />
                </el-form-item>
                <el-form-item label="Contact" required>
                  <el-input v-model="customer.contact_person" />
                </el-form-item>
                <el-form-item label="Phone" required>
                  <el-input v-model="customer.phone" />
                </el-form-item>
                <el-form-item label="WeChat (optional)">
                  <el-input v-model="customer.wechat" />
                </el-form-item>
                <el-form-item label="Email (optional)">
                  <el-input v-model="customer.email" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Company (optional)">
                  <el-input v-model="customer.company" />
                </el-form-item>
                <el-form-item label="Region (optional)">
                  <el-input v-model="customer.region" />
                </el-form-item>
                <el-form-item label="Source Channel (optional)">
                  <el-input v-model="customer.source_channel" />
                </el-form-item>
                <el-form-item label="Sales Rep">
                  <el-input v-model="customer.sales_name" disabled />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item v-if="editMode">
              <el-button type="primary" @click="handleSave">Save</el-button>
              <el-button @click="editMode = false">Cancel</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- Contracts -->
        <el-tab-pane label="Contracts" name="contracts">
          <div class="section-toolbar">
            <el-button type="primary" size="small" :icon="Plus" @click="openContractDialog">
              New Contract
            </el-button>
          </div>
          <el-table :data="contracts" stripe empty-text="No contracts">
            <el-table-column prop="contract_no" label="Contract No" min-width="150" />
            <el-table-column prop="contract_amount" label="Amount" width="120">
              <template #default="{ row }">¥{{ formatAmount(row.contract_amount) }}</template>
            </el-table-column>
            <el-table-column prop="sign_date" label="Sign Date" width="120" />
            <el-table-column prop="delivery_date" label="Delivery Date" width="120" />
            <el-table-column label="Actions" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="editContract(row)">Edit</el-button>
                <el-popconfirm title="Confirm delete?" @confirm="deleteContract(row.id)">
                  <template #reference>
                    <el-button link type="danger">Delete</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Tasks -->
        <el-tab-pane label="Tasks" name="tasks">
          <div class="section-toolbar">
            <el-button type="primary" size="small" :icon="Plus" @click="openTaskDialog">
              New Task
            </el-button>
          </div>
          <el-table :data="tasks" stripe empty-text="No tasks">
            <el-table-column prop="name" label="Task Name" min-width="150" />
            <el-table-column prop="assignee_name" label="Assignee" width="120" />
            <el-table-column prop="due_date" label="Due Date" width="120" />
            <el-table-column prop="priority" label="Priority" width="90">
              <template #default="{ row }">
                <el-tag :type="row.priority === 'high' ? 'danger' : row.priority === 'medium' ? 'warning' : 'info'" size="small">
                  {{ { high: 'High', medium: 'Medium', low: 'Low', urgent: 'Urgent' }[row.priority] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="Status" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'in_progress' ? 'primary' : 'info'" size="small">
                  {{ { pending: 'Pending', in_progress: 'In Progress', completed: 'Completed' }[row.status] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Actions" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="editTask(row)">Edit</el-button>
                <el-popconfirm title="Confirm delete?" @confirm="deleteTask(row.id)">
                  <template #reference>
                    <el-button link type="danger">Delete</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Communications -->
        <el-tab-pane label="Communications" name="communications">
          <div class="section-toolbar">
            <el-button type="primary" size="small" :icon="Plus" @click="openCommDialog">
              Add Record
            </el-button>
          </div>
          <div class="timeline">
            <div v-for="item in communications" :key="item.id" class="timeline-item">
              <div class="timeline-dot" />
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="timeline-type">{{ item.channel === 'phone' ? 'Phone' : item.channel === 'wechat' ? 'WeChat' : item.channel === 'meeting' ? 'Meeting' : item.channel === 'email' ? 'Email' : 'Other' }}</span>
                  <span class="timeline-time">{{ item.created_at }}</span>
                </div>
                <div class="timeline-body">{{ item.content }}</div>
                <div class="timeline-footer">
                  <span>{{ item.user_name }}</span>
                  <div>
                    <el-button link type="primary" size="small" @click="editComm(item)">Edit</el-button>
                    <el-popconfirm title="Confirm delete?" @confirm="deleteComm(item.id)">
                      <template #reference>
                        <el-button link type="danger" size="small">Delete</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
            </div>
            <el-empty v-if="communications.length === 0" description="No communication records" :image-size="60" />
          </div>
        </el-tab-pane>

        <!-- Payments -->
        <el-tab-pane label="Payments" name="payments">
          <div class="section-toolbar">
            <el-button type="primary" size="small" :icon="Plus" @click="openPaymentDialog">
              Add Payment
            </el-button>
          </div>
          <el-table :data="payments" stripe empty-text="No payment records">
            <el-table-column prop="amount" label="Amount" width="120">
              <template #default="{ row }">¥{{ formatAmount(row.amount) }}</template>
            </el-table-column>
            <el-table-column prop="payment_date" label="Payment Date" width="120" />
            <el-table-column prop="payment_type" label="Payment Type" width="120" />
            <el-table-column prop="notes" label="Notes" min-width="150" />
            <el-table-column label="Actions" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="editPayment(row)">Edit</el-button>
                <el-popconfirm title="Confirm delete?" @confirm="deletePayment(row.id)">
                  <template #reference>
                    <el-button link type="danger">Delete</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Documents -->
        <el-tab-pane label="Documents" name="documents">
          <div class="section-toolbar">
            <el-button type="primary" size="small" :icon="Upload" @click="openDocDialog">
              Upload Document
            </el-button>
          </div>
          <el-table :data="documents" stripe empty-text="No documents">
            <el-table-column prop="file_name" label="File Name" min-width="200">
              <template #default="{ row }">
                <el-icon><Document /></el-icon>
                {{ row.file_name }}
              </template>
            </el-table-column>
            <el-table-column prop="category" label="Category" width="120" />
            <el-table-column prop="file_size" label="Size" width="100">
              <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column prop="uploaded_by_name" label="Uploaded By" width="100" />
            <el-table-column label="Actions" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="downloadDoc(row)">Download</el-button>
                <el-button link type="primary" @click="editDoc(row)">Edit</el-button>
                <el-popconfirm title="Confirm delete?" @confirm="deleteDoc(row.id)">
                  <template #reference>
                    <el-button link type="danger">Delete</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Contract Dialog -->
    <el-dialog v-model="showContractDialog" :title="editContractId ? 'Edit Contract' : 'New Contract'" width="600px">
      <el-form :model="contractForm" label-position="top" v-if="contractForm">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Contract No" required>
              <el-input v-model="contractForm.contract_no" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Amount (optional)">
              <el-input-number v-model="contractForm.contract_amount" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Sign Date (optional)">
              <el-date-picker v-model="contractForm.sign_date" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Delivery Date (optional)">
              <el-date-picker v-model="contractForm.delivery_date" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="Payment Terms (optional)">
          <el-input v-model="contractForm.payment_terms" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showContractDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveContract">Save</el-button>
      </template>
    </el-dialog>

    <!-- Task Dialog -->
    <el-dialog v-model="showTaskDialog" :title="editTaskId ? 'Edit Task' : 'New Task'" width="600px">
      <el-form :model="taskForm" label-position="top" v-if="taskForm">
        <el-form-item label="Task Name" required>
          <el-input v-model="taskForm.name" />
        </el-form-item>
        <el-form-item label="Description (optional)">
          <el-input v-model="taskForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Priority (optional)">
              <el-select v-model="taskForm.priority" style="width:100%">
                <el-option label="Low" value="low" />
                <el-option label="Medium" value="medium" />
                <el-option label="High" value="high" />
                <el-option label="Urgent" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Status (optional)">
              <el-select v-model="taskForm.status" style="width:100%">
                <el-option label="Pending" value="pending" />
                <el-option label="In Progress" value="in_progress" />
                <el-option label="Completed" value="completed" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Start Date (optional)">
              <el-date-picker v-model="taskForm.start_date" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Due Date (optional)">
              <el-date-picker v-model="taskForm.due_date" type="date" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="showTaskDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveTask">Save</el-button>
      </template>
    </el-dialog>

    <!-- Communication Dialog -->
    <el-dialog v-model="showCommDialog" :title="editCommId ? 'Edit Communication' : 'New Communication'" width="600px">
      <el-form :model="commForm" label-position="top" v-if="commForm">
        <el-form-item label="Channel" required>
          <el-select v-model="commForm.channel" style="width:100%">
            <el-option label="Phone" value="phone" />
            <el-option label="WeChat" value="wechat" />
            <el-option label="Meeting" value="meeting" />
            <el-option label="Email" value="email" />
          </el-select>
        </el-form-item>
        <el-form-item label="Content (optional)">
          <el-input v-model="commForm.content" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="Next Action (optional)">
          <el-input v-model="commForm.next_action" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Next Action Date (optional)">
          <el-date-picker v-model="commForm.next_action_date" type="date" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCommDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveComm">Save</el-button>
      </template>
    </el-dialog>

    <!-- Payment Dialog -->
    <el-dialog v-model="showPaymentDialog" :title="editPaymentId ? 'Edit Payment' : 'New Payment'" width="500px">
      <el-form :model="paymentForm" label-position="top" v-if="paymentForm">
        <el-form-item label="Amount" required>
          <el-input-number v-model="paymentForm.amount" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="Payment Date (optional)">
          <el-date-picker v-model="paymentForm.payment_date" type="date" style="width:100%" />
        </el-form-item>
        <el-form-item label="Payment Type" required>
          <el-select v-model="paymentForm.payment_type" style="width:100%">
            <el-option label="Deposit" value="deposit" />
            <el-option label="Milestone" value="milestone" />
            <el-option label="Final" value="final" />
          </el-select>
        </el-form-item>
        <el-form-item label="Invoice No (optional)">
          <el-input v-model="paymentForm.invoice_no" />
        </el-form-item>
        <el-form-item label="Notes (optional)">
          <el-input v-model="paymentForm.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPaymentDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSavePayment">Save</el-button>
      </template>
    </el-dialog>

    <!-- Document Dialog -->
    <el-dialog v-model="showDocDialog" title="Upload Document" width="500px">
      <el-form :model="docForm" label-position="top" v-if="docForm">
        <el-form-item label="File Category (optional)">
          <el-select v-model="docForm.category" style="width:100%">
            <el-option label="Contract" value="contract" />
            <el-option label="Requirement" value="requirement" />
            <el-option label="Acceptance" value="acceptance" />
            <el-option label="Invoice" value="invoice" />
            <el-option label="Other" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="File" required>
          <el-upload
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
          >
            <el-button type="primary">Select File</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDocDialog = false">Cancel</el-button>
        <el-button type="primary" @click="handleSaveDoc">Upload</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerStore } from '@/stores/customer'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Top, Edit, Delete, Plus, Upload, Check, Document,
  Iphone, ChatDotSquare, Message, OfficeBuilding, Location, Avatar
} from '@element-plus/icons-vue'
import { contractApi, taskApi, communicationApi, paymentApi, documentApi } from '@/api'
import StageTag from '@/components/StageTag.vue'
import AlertBadge from '@/components/AlertBadge.vue'

const route = useRoute()
const router = useRouter()
const customerStore = useCustomerStore()
const userStore = useUserStore()

const customer = ref(null)
const loading = ref(false)
const editMode = ref(false)
const activeTab = ref('info')

// Sub-module data
const contracts = ref([])
const tasks = ref([])
const communications = ref([])
const payments = ref([])
const documents = ref([])

const stageList = [
  { id: 1, name: 'Lead' },
  { id: 2, name: 'Consult' },
  { id: 3, name: 'Contract' },
  { id: 4, name: 'Requirements' },
  { id: 5, name: 'Service' },
  { id: 6, name: 'Delivery' },
  { id: 7, name: 'Payment' },
  { id: 8, name: 'Completed' }
]

// Dialog states
const showContractDialog = ref(false)
const showTaskDialog = ref(false)
const showCommDialog = ref(false)
const showPaymentDialog = ref(false)
const showDocDialog = ref(false)

// Form refs
const editContractId = ref(null)
const contractForm = ref(null)
const editTaskId = ref(null)
const taskForm = ref(null)
const editCommId = ref(null)
const commForm = ref(null)
const editPaymentId = ref(null)
const paymentForm = ref(null)
const docForm = ref(null)
const selectedFile = ref(null)

onMounted(async () => {
  await loadCustomer()
})

watch(() => route.params.id, async () => {
  await loadCustomer()
})

async function loadCustomer() {
  const id = route.params.id
  if (!id) return
  loading.value = true
  try {
    customer.value = await customerStore.fetchCustomerDetail(id)
    await Promise.all([
      loadContracts(),
      loadTasks(),
      loadCommunications(),
      loadPayments(),
      loadDocuments()
    ])
  } catch {
    ElMessage.error('Failed to load customer details')
    router.push('/customer/list')
  } finally {
    loading.value = false
  }
}

async function loadContracts() {
  try {
    const res = await contractApi.getByCustomer(route.params.id)
    const data = res.data || res || []
    contracts.value = Array.isArray(data) ? data : (data ? [data] : [])
  } catch { contracts.value = [] }
}

async function loadTasks() {
  try {
    const res = await taskApi.list({ customer_id: route.params.id })
    tasks.value = res.data?.items || res.data || []
  } catch { tasks.value = [] }
}

async function loadCommunications() {
  try {
    const res = await communicationApi.list({ customer_id: route.params.id })
    communications.value = res.data?.items || res.data || []
  } catch { communications.value = [] }
}

async function loadPayments() {
  try {
    const res = await paymentApi.list({ customer_id: route.params.id })
    payments.value = res.data?.items || res.data || []
  } catch { payments.value = [] }
}

async function loadDocuments() {
  try {
    const res = await documentApi.list({ customer_id: route.params.id })
    documents.value = res.data?.items || res.data || []
  } catch { documents.value = [] }
}

async function handleAdvance() {
  if (customer.value.stage >= 8) {
    ElMessage.info('Customer has completed all stages')
    return
  }
  const nextStage = customer.value.stage + 1
  try {
    await customerStore.advanceStage(customer.value.id, { new_stage: nextStage })
    ElMessage.success('Stage advanced')
    await loadCustomer()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Advance failed')
  }
}

async function handleSave() {
  const c = customer.value
  if (!c.name || !c.name.trim()) {
    ElMessage.warning('Customer Name is required')
    return
  }
  if (!c.contact_person || !c.contact_person.trim()) {
    ElMessage.warning('Contact is required')
    return
  }
  if (!c.phone || !c.phone.trim()) {
    ElMessage.warning('Phone is required')
    return
  }
  const payload = {
    name: c.name,
    contact_person: c.contact_person,
    phone: c.phone,
    wechat: c.wechat,
    email: c.email,
    company: c.company,
    region: c.region,
    source_channel: c.source_channel
  }
  try {
    await customerStore.updateCustomer(c.id, payload)
    ElMessage.success('Saved')
    editMode.value = false
    await loadCustomer()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Save failed')
  }
}

async function handleDelete() {
  try {
    await customerStore.deleteCustomer(customer.value.id)
    ElMessage.success('Deleted')
    router.push('/customer/list')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Delete failed')
  }
}

function formatAmount(val) {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (isNaN(num)) return '-'
  return num.toLocaleString()
}

// Document helpers
function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1024 / 1024).toFixed(1) + 'MB'
}

async function downloadDoc(row) {
  try {
    const res = await documentApi.download(row.id)
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.file_name || 'download')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('Download failed')
  }
}

// --- CRUD Handlers ---

// Open "create" dialogs with a freshly initialized form (otherwise v-if form stays hidden)
const openContractDialog = () => {
  editContractId.value = null
  contractForm.value = { contract_no: '', contract_amount: 0, sign_date: null, delivery_date: null, payment_terms: '' }
  showContractDialog.value = true
}

const openTaskDialog = () => {
  editTaskId.value = null
  taskForm.value = { name: '', description: '', priority: 'medium', status: 'pending', start_date: null, due_date: null }
  showTaskDialog.value = true
}

const openCommDialog = () => {
  editCommId.value = null
  commForm.value = { channel: '', content: '', next_action: '', next_action_date: null }
  showCommDialog.value = true
}

const openPaymentDialog = () => {
  editPaymentId.value = null
  paymentForm.value = { amount: 0, payment_date: null, payment_type: '', invoice_no: '', notes: '' }
  showPaymentDialog.value = true
}

const openDocDialog = () => {
  docForm.value = { category: 'other' }
  selectedFile.value = null
  showDocDialog.value = true
}

// Convert el-date-picker value to 'YYYY-MM-DD' (backend expects a plain date, no time part)
const pad2 = (n) => String(n).padStart(2, '0')
const toDateStr = (v) => {
  if (!v) return null
  if (v instanceof Date) return `${v.getFullYear()}-${pad2(v.getMonth() + 1)}-${pad2(v.getDate())}`
  return String(v).slice(0, 10)
}

// Contract handlers
const handleSaveContract = async () => {
  if (!contractForm.value) return
  if (!contractForm.value.contract_no || !contractForm.value.contract_no.trim()) {
    ElMessage.warning('Contract No is required')
    return
  }
  try {
    const payload = {
      ...contractForm.value,
      sign_date: toDateStr(contractForm.value.sign_date),
      delivery_date: toDateStr(contractForm.value.delivery_date),
    }
    if (editContractId.value) {
      await contractApi.update(editContractId.value, payload)
    } else {
      await contractApi.create(route.params.id, payload)
    }
    ElMessage.success(editContractId.value ? 'Contract updated' : 'Contract created')
    showContractDialog.value = false
    loadContracts()
  } catch (err) {
    ElMessage.error('Failed to save contract')
  }
}

const handleEditContract = (item) => {
  editContractId.value = item.id
  contractForm.value = { ...item }
  showContractDialog.value = true
}

const handleDeleteContract = async (id) => {
  try {
    await contractApi.delete(id)
    ElMessage.success('Contract deleted')
    loadContracts()
  } catch {
    ElMessage.error('Failed to delete contract')
  }
}

// Use aliases for template bindings
const editContract = handleEditContract
const deleteContract = handleDeleteContract

// Task handlers
const handleSaveTask = async () => {
  if (!taskForm.value) return
  if (!taskForm.value.name || !taskForm.value.name.trim()) {
    ElMessage.warning('Task Name is required')
    return
  }
  try {
    const payload = {
      ...taskForm.value,
      start_date: toDateStr(taskForm.value.start_date),
      due_date: toDateStr(taskForm.value.due_date),
    }
    if (editTaskId.value) {
      await taskApi.update(editTaskId.value, payload)
    } else {
      await taskApi.create(route.params.id, payload)
    }
    ElMessage.success(editTaskId.value ? 'Task updated' : 'Task created')
    showTaskDialog.value = false
    loadTasks()
  } catch (err) {
    ElMessage.error('Failed to save task')
  }
}

const handleEditTask = (item) => {
  editTaskId.value = item.id
  taskForm.value = { ...item }
  showTaskDialog.value = true
}

const handleDeleteTask = async (id) => {
  try {
    await taskApi.delete(id)
    ElMessage.success('Task deleted')
    loadTasks()
  } catch {
    ElMessage.error('Failed to delete task')
  }
}

const editTask = handleEditTask
const deleteTask = handleDeleteTask

// Communication handlers
const handleSaveComm = async () => {
  if (!commForm.value) return
  if (!commForm.value.channel) {
    ElMessage.warning('Channel is required')
    return
  }
  try {
    const payload = {
      ...commForm.value,
      next_action_date: toDateStr(commForm.value.next_action_date),
    }
    if (editCommId.value) {
      await communicationApi.update(editCommId.value, payload)
    } else {
      await communicationApi.create(route.params.id, payload)
    }
    ElMessage.success(editCommId.value ? 'Communication updated' : 'Communication created')
    showCommDialog.value = false
    loadCommunications()
  } catch (err) {
    ElMessage.error('Failed to save communication')
  }
}

const handleEditComm = (item) => {
  editCommId.value = item.id
  commForm.value = { ...item }
  showCommDialog.value = true
}

const handleDeleteComm = async (id) => {
  try {
    await communicationApi.delete(id)
    ElMessage.success('Communication deleted')
    loadCommunications()
  } catch {
    ElMessage.error('Failed to delete communication')
  }
}

const editComm = handleEditComm
const deleteComm = handleDeleteComm

// Payment handlers
const handleSavePayment = async () => {
  if (!paymentForm.value) return
  if (!paymentForm.value.amount || Number(paymentForm.value.amount) <= 0) {
    ElMessage.warning('Amount is required and must be greater than 0')
    return
  }
  if (!paymentForm.value.payment_type) {
    ElMessage.warning('Payment Type is required')
    return
  }
  try {
    const payload = {
      ...paymentForm.value,
      payment_date: toDateStr(paymentForm.value.payment_date),
    }
    if (editPaymentId.value) {
      await paymentApi.update(editPaymentId.value, payload)
    } else {
      await paymentApi.create(route.params.id, payload)
    }
    ElMessage.success(editPaymentId.value ? 'Payment updated' : 'Payment created')
    showPaymentDialog.value = false
    loadPayments()
  } catch (err) {
    ElMessage.error('Failed to save payment')
  }
}

const handleEditPayment = (item) => {
  editPaymentId.value = item.id
  paymentForm.value = { ...item }
  showPaymentDialog.value = true
}

const handleDeletePayment = async (id) => {
  try {
    await paymentApi.delete(id)
    ElMessage.success('Payment deleted')
    loadPayments()
  } catch {
    ElMessage.error('Failed to delete payment')
  }
}

const editPayment = handleEditPayment
const deletePayment = handleDeletePayment

// Document handlers
const handleSaveDoc = async () => {
  if (!docForm.value || !selectedFile.value) return
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('category', docForm.value.category || 'other')
    await documentApi.create(route.params.id, formData)
    ElMessage.success('Document uploaded')
    showDocDialog.value = false
    selectedFile.value = null
    loadDocuments()
  } catch (err) {
    ElMessage.error('Failed to upload document')
  }
}

const handleFileChange = (uploadFile) => {
  selectedFile.value = uploadFile.raw
}

const handleEditDoc = (item) => {
  ElMessage.info('Edit document metadata - right-click rename on table row')
}

const handleDeleteDoc = async (id) => {
  try {
    await documentApi.delete(id)
    ElMessage.success('Document deleted')
    loadDocuments()
  } catch {
    ElMessage.error('Failed to delete document')
  }
}

const editDoc = handleEditDoc
const deleteDoc = handleDeleteDoc
</script>

<style scoped>
.detail-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-title h2 {
  font-size: 22px;
  font-weight: 600;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-header-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #606266;
}

.detail-header-info span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Stage Progress Bar */
.stage-progress {
  display: flex;
  align-items: flex-start;
  gap: 0;
  position: relative;
}

.stage-progress-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  min-width: 0;
}

.stage-progress-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  z-index: 1;
  position: relative;
}

.stage-progress-item.future .stage-progress-dot {
  background: #e4e7ed !important;
  color: #909399;
}

.stage-progress-item.current .stage-progress-dot {
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.3);
}

.stage-progress-label {
  font-size: 11px;
  margin-top: 6px;
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
}

.stage-progress-item.current .stage-progress-label {
  font-weight: 700;
}

.stage-progress-line {
  position: absolute;
  top: 15px;
  left: calc(50% + 16px);
  right: calc(-50% + 16px);
  height: 2px;
  background: #e4e7ed;
}

.stage-progress-item:last-child .stage-progress-line {
  display: none;
}

.stage-progress-line.completed-line {
  background: #409EFF;
}

.stage-current-info {
  font-size: 13px;
  color: #606266;
}

/* Tab Toolbar */
.section-toolbar {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

/* Timeline Style */
.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  padding-bottom: 20px;
  padding-left: 20px;
  border-left: 2px solid #e4e7ed;
  margin-left: 4px;
}

.timeline-item:last-child {
  border-left-color: transparent;
}

.timeline-dot {
  position: absolute;
  left: -6px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409EFF;
  border: 2px solid #fff;
}

.timeline-content {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.timeline-type {
  font-weight: 600;
  font-size: 13px;
}

.timeline-time {
  font-size: 12px;
  color: #909399;
}

.timeline-body {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.6;
}

.timeline-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.mt-16 {
  margin-top: 16px;
}
</style>
