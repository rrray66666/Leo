<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Import/Export</h2>
    </div>

    <el-row :gutter="24">
      <!-- Import -->
      <el-col :span="12">
        <div class="detail-section">
          <h3>Import Customers</h3>
          <div class="import-area">
            <el-upload
              drag
              action="/api/v1/customers/import"
              :headers="uploadHeaders"
              :on-success="onUploadSuccess"
              :on-error="onUploadError"
              accept=".xlsx,.xls"
              :limit="1"
            >
              <el-icon :size="48" color="#409EFF"><UploadFilled /></el-icon>
              <div class="upload-text">
                <span>Drag & drop Excel files here, or<em> click to upload</em></span>
              </div>
              <template #tip>
                <div class="upload-tip">
                  Only .xlsx and .xls files supported
                </div>
              </template>
            </el-upload>
          </div>
          <div class="import-actions mt-16">
            <el-button :icon="Download" @click="downloadTemplate">Download Template</el-button>
          </div>

          <!-- Import History -->
          <div class="mt-16">
            <h4 class="section-subtitle">Import History</h4>
            <el-table :data="importHistory" stripe size="small" empty-text="No import records">
              <el-table-column prop="created_at" label="Time" width="140" />
              <el-table-column prop="file_name" label="File Name" min-width="120" />
              <el-table-column prop="success_count" label="Success" width="60" />
              <el-table-column prop="fail_count" label="Failed" width="60" />
              <el-table-column prop="status" label="Status" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                    {{ row.status === 'completed' ? 'Completed' : 'Processing' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-col>

      <!-- Export -->
      <el-col :span="12">
        <div class="detail-section">
          <h3>Export Customers</h3>
          <el-form :model="exportForm" label-width="100px">
            <el-form-item label="Stage">
              <el-select v-model="exportForm.stage" placeholder="All Stages" clearable style="width:100%">
                <el-option v-for="s in stageOptions" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="Region">
              <el-input v-model="exportForm.region" placeholder="Optional" />
            </el-form-item>
            <el-form-item label="Sales Rep">
              <el-select v-model="exportForm.sales_id" placeholder="All Sales" clearable filterable style="width:100%">
                <el-option v-for="s in salesList" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="Date Range">
              <el-date-picker
                v-model="exportForm.date_range"
                type="daterange"
                range-separator="to"
                start-placeholder="Start Date"
                end-placeholder="End Date"
                value-format="YYYY-MM-DD"
                style="width:100%"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Download" :loading="exporting" @click="handleExport">
                Export Excel
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { customerApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'

const exporting = ref(false)
const importHistory = ref([])

const stageOptions = [
  { value: 1, label: 'Lead' }, { value: 2, label: 'Consult' },
  { value: 3, label: 'Contract' }, { value: 4, label: 'Requirements' },
  { value: 5, label: 'Service' }, { value: 6, label: 'Delivery' },
  { value: 7, label: 'Payment' }, { value: 8, label: 'Completed' }
]

const salesList = ref([])

const exportForm = reactive({
  stage: '',
  region: '',
  sales_id: '',
  date_range: null
})

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`
}))

onMounted(() => {
  // Simulate loading import history
  importHistory.value = []
})

function onUploadSuccess(response) {
  ElMessage.success('Import successful')
}

function onUploadError(err) {
  ElMessage.error(err?.message || 'Import failed')
}

async function downloadTemplate() {
  try {
    const res = await customerApi.downloadTemplate()
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'customer_import_template.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('Template downloaded')
  } catch {
    ElMessage.error('Template download failed')
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const params = {}
    if (exportForm.stage) params.stage = exportForm.stage
    if (exportForm.region) params.region = exportForm.region
    if (exportForm.sales_id) params.sales_id = exportForm.sales_id
    if (exportForm.date_range) {
      params.start_date = exportForm.date_range[0]
      params.end_date = exportForm.date_range[1]
    }
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
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.import-area {
  padding: 20px 0;
}

.upload-text {
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.upload-text em {
  color: #409EFF;
  font-style: normal;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  text-align: center;
}

.import-actions {
  display: flex;
  gap: 8px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.mt-16 {
  margin-top: 16px;
}
</style>
