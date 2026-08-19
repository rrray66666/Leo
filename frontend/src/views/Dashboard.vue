<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Dashboard</h2>
      <el-button :icon="Refresh" @click="loadAllData">Refresh</el-button>
    </div>

    <!-- Overview cards -->
    <el-row :gutter="16" class="mb-16">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">Total Customers</div>
          <div class="stat-value" style="color:#409EFF">{{ stats.total_customers || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">New This Month</div>
          <div class="stat-value" style="color:#67C23A">{{ stats.monthly_new || 0 }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">Payments This Month</div>
          <div class="stat-value" style="color:#E6A23C">¥{{ formatAmount(stats.monthly_payment) }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">Alert Customers</div>
          <div class="stat-value" style="color:#F56C6C">{{ stats.overdue_count || 0 }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- Charts -->
    <el-row :gutter="16">
      <!-- Funnel chart -->
      <el-col :span="12">
        <div class="chart-card">
          <h3>Customer Distribution</h3>
          <div class="funnel-chart">
            <div
              v-for="item in funnelData"
              :key="item.stage"
              class="funnel-bar-wrapper"
            >
              <div class="funnel-label">
                <StageTag :stage="item.stage" size="small" />
              </div>
              <div class="funnel-bar-container">
                <div
                  class="funnel-bar"
                  :class="`stage-bg-${item.stage}`"
                  :style="{ width: funnelPercent(item) + '%' }"
                >
                  <span class="funnel-count">{{ item.count }}</span>
                </div>
              </div>
            </div>
            <el-empty v-if="funnelData.length === 0" description="No data" :image-size="60" />
          </div>
        </div>
      </el-col>

      <!-- Sales workload -->
      <el-col :span="12">
        <div class="chart-card">
          <h3>Sales Workload</h3>
          <div class="sales-chart">
            <div
              v-for="item in salesData"
              :key="item.user_id || item.user_name"
              class="sales-bar-wrapper"
            >
              <div class="sales-label">{{ item.user_name }}</div>
              <div class="sales-bar-container">
                <div
                  class="sales-bar"
                  :style="{ width: salesPercent(item) + '%' }"
                >
                  <span class="sales-count">{{ item.customer_count }}</span>
                </div>
              </div>
            </div>
            <el-empty v-if="salesData.length === 0" description="No data" :image-size="60" />
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Payment statistics -->
    <el-row :gutter="16" class="mt-16">
      <el-col :span="24">
        <div class="chart-card">
          <h3>Monthly Payment Trend</h3>
          <div class="payment-chart">
            <div class="payment-bars">
              <div
                v-for="item in paymentData"
                :key="item.month"
                class="payment-bar-wrapper"
              >
                <div class="payment-bar-container">
                  <div
                    class="payment-bar"
                    :style="{ height: paymentHeight(item) + '%' }"
                  >
                    <span class="payment-amount">¥{{ formatAmount(item.total) }}</span>
                  </div>
                </div>
                <div class="payment-label">{{ item.month }}</div>
              </div>
            </div>
            <el-empty v-if="paymentData.length === 0" description="No payment data" :image-size="60" />
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { dashboardApi } from '@/api'
import { Refresh } from '@element-plus/icons-vue'
import StageTag from '@/components/StageTag.vue'

const stats = reactive({
  total_customers: 0,
  monthly_new: 0,
  monthly_payment: 0,
  alert_count: 0
})

const funnelData = ref([])
const salesData = ref([])
const paymentData = ref([])

const maxFunnelCount = ref(1)
const maxSalesCount = ref(1)
const maxPaymentAmount = ref(1)

function formatAmount(val) {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (isNaN(num)) return '-'
  return num.toLocaleString()
}

onMounted(async () => {
  await loadAllData()
})

async function loadAllData() {
  await Promise.all([
    loadStats(),
    loadFunnel(),
    loadSales(),
    loadPayments()
  ])
}

async function loadStats() {
  try {
    const res = await dashboardApi.getStats()
    const data = res.data || res
    Object.assign(stats, data)
  } catch { /* silent */ }
}

async function loadFunnel() {
  try {
    const res = await dashboardApi.getFunnel()
    const data = res.data || res || []
    funnelData.value = data
    if (data.length > 0) {
      maxFunnelCount.value = Math.max(...data.map(d => d.count || 0), 1)
    }
  } catch { funnelData.value = [] }
}

async function loadSales() {
  try {
    const res = await dashboardApi.getSales()
    const data = res.data || res || []
    salesData.value = data
    if (data.length > 0) {
      maxSalesCount.value = Math.max(...data.map(d => d.customer_count || 0), 1)
    }
  } catch { salesData.value = [] }
}

async function loadPayments() {
  try {
    const res = await dashboardApi.getPayments({ year: new Date().getFullYear() })
    const data = res.data || res || []
    paymentData.value = data
    if (data.length > 0) {
      maxPaymentAmount.value = Math.max(...data.map(d => d.total || 0), 1)
    }
  } catch { paymentData.value = [] }
}

function funnelPercent(item) {
  return ((item.count || 0) / maxFunnelCount.value) * 100
}

function salesPercent(item) {
  return ((item.customer_count || 0) / maxSalesCount.value) * 100
}

function paymentHeight(item) {
  return Math.max(((item.total || 0) / maxPaymentAmount.value) * 100, 5)
}
</script>

<style scoped>
.mb-16 { margin-bottom: 16px; }
.mt-16 { margin-top: 16px; }

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  margin-bottom: 16px;
}

.chart-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #303133;
}

/* Funnel */
.funnel-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.funnel-label {
  width: 80px;
  flex-shrink: 0;
  text-align: right;
}

.funnel-bar-container {
  flex: 1;
  height: 28px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.funnel-bar {
  height: 100%;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  transition: width 0.5s ease;
  min-width: 30px;
}

.funnel-count {
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

/* Sales chart */
.sales-bar-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.sales-label {
  width: 80px;
  font-size: 13px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sales-bar-container {
  flex: 1;
  height: 28px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.sales-bar {
  height: 100%;
  background: #409EFF;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  transition: width 0.5s ease;
  min-width: 30px;
}

.sales-count {
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

/* Payment chart */
.payment-bars {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  height: 220px;
  padding: 0 20px;
}

.payment-bar-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.payment-bar-container {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.payment-bar {
  width: 40px;
  background: linear-gradient(180deg, #36CFC9, #409EFF);
  border-radius: 4px 4px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4px;
  transition: height 0.5s ease;
  min-height: 8px;
}

.payment-amount {
  font-size: 10px;
  color: #fff;
  writing-mode: vertical-lr;
  text-orientation: mixed;
}

.payment-label {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
