<template>
  <div class="kanban-page">
    <!-- Filter bar -->
    <div class="filter-bar">
      <el-select v-model="filters.sales" placeholder="Filter by sales" clearable filterable>
        <el-option
          v-for="s in salesList"
          :key="s.id"
          :label="s.name"
          :value="s.id"
        />
      </el-select>
      <el-select v-model="filters.region" placeholder="Filter by region" clearable filterable>
        <el-option
          v-for="r in regionList"
          :key="r"
          :label="r"
          :value="r"
        />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="Search customer name..."
        clearable
        :prefix-icon="Search"
        @change="loadData"
        @clear="loadData"
      />
      <el-button type="primary" :icon="Search" @click="loadData">Filter</el-button>
      <el-button :icon="Refresh" @click="resetFilters">Reset</el-button>
    </div>

    <!-- Kanban columns -->
    <div class="kanban-container" v-loading="customerStore.loading">
      <div
        v-for="column in kanbanColumns"
        :key="column.id"
        class="kanban-column"
        @dragover.prevent="onDragOver"
        @drop="onDrop($event, column.id)"
      >
        <div class="kanban-column-header" :class="`stage-bg-${column.id}`">
          <span :class="`stage-color-${column.id}`">
            {{ column.name }}
          </span>
          <el-tag :type="column.id === 8 ? 'success' : 'info'" size="small" effect="plain">
            {{ column.count }}
          </el-tag>
        </div>
        <div class="kanban-column-body">
          <CustomerCard
            v-for="customer in column.customers"
            :key="customer.id"
            :customer="customer"
            @drag-start="onDragStart(customer)"
            @drag-end="onDragEnd"
          />
          <el-empty v-if="column.customers.length === 0" description="No customers" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- Stage advance confirmation dialog -->
    <el-dialog
      v-model="advanceDialog.visible"
      title="Advance Stage"
      width="400px"
    >
      <div class="advance-dialog-content">
        <p>Confirm advancing customer <strong>{{ advanceDialog.customerName }}</strong> from
          <StageTag :stage="advanceDialog.fromStage" size="small" />
          to
          <StageTag :stage="advanceDialog.toStage" size="small" />
          ?
        </p>
        <el-form :model="advanceDialog.form" label-width="80px" class="mt-16">
          <el-form-item label="Notes (optional)">
            <el-input
              v-model="advanceDialog.form.remark"
              type="textarea"
              :rows="3"
              placeholder="Optional, add notes"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="advanceDialog.visible = false">Cancel</el-button>
        <el-button type="primary" :loading="advanceDialog.loading" @click="confirmAdvance">
          Confirm
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useCustomerStore } from '@/stores/customer'
import { userApi, dictApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import CustomerCard from '@/components/CustomerCard.vue'
import StageTag from '@/components/StageTag.vue'

const customerStore = useCustomerStore()

const filters = reactive({
  sales: '',
  region: '',
  keyword: ''
})

const salesList = ref([])
const regionList = ref([])

// drag state
const dragCustomer = ref(null)

const advanceDialog = reactive({
  visible: false,
  loading: false,
  customerName: '',
  fromStage: 0,
  toStage: 0,
  customerId: null,
  form: { remark: '' }
})

const kanbanColumns = computed(() => customerStore.kanbanByStage)

let pollTimer = null

onMounted(async () => {
  await Promise.all([loadData(), loadFilterOptions()])
  // 30s auto refresh
  pollTimer = setInterval(loadData, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
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
  const params = {}
  if (filters.sales) params.sales_id = filters.sales
  if (filters.region) params.region = filters.region
  if (filters.keyword) params.keyword = filters.keyword
  try {
    await customerStore.fetchKanban(params)
  } catch {
    // Token expired or network error: keep the last data on screen
    // instead of breaking the mounted hook / freezing the page.
  }
}

function resetFilters() {
  Object.assign(filters, { sales: '', region: '', keyword: '' })
  loadData()
}

function onDragStart(customer) {
  dragCustomer.value = customer
}

function onDragEnd() {
  dragCustomer.value = null
}

function onDragOver(e) {
  e.dataTransfer.dropEffect = 'move'
}

function onDrop(e, targetStage) {
  if (!dragCustomer.value) return

  const fromStage = dragCustomer.value.stage
  if (fromStage === targetStage) return

  // can only advance forward, not backward
  if (targetStage < fromStage) {
    ElMessage.warning('Cannot move customer backwards')
    return
  }

  advanceDialog.customerName = dragCustomer.value.name
  advanceDialog.fromStage = fromStage
  advanceDialog.toStage = targetStage
  advanceDialog.customerId = dragCustomer.value.id
  advanceDialog.form.remark = ''
  advanceDialog.visible = true
}

async function confirmAdvance() {
  advanceDialog.loading = true
  try {
    await customerStore.advanceStage(advanceDialog.customerId, {
      new_stage: advanceDialog.toStage,
      remark: advanceDialog.form.remark
    })
    ElMessage.success('Stage advanced successfully')
    advanceDialog.visible = false
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Failed to advance stage')
  } finally {
    advanceDialog.loading = false
  }
}
</script>

<style scoped>
.kanban-page {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 0;
  padding: 0 0 16px 0;
}

.filter-bar .el-select,
.filter-bar .el-input {
  width: 180px;
}

.kanban-container {
  flex: 1;
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.advance-dialog-content p {
  font-size: 14px;
  line-height: 1.8;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
