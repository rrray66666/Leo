<template>
  <div
    class="customer-card"
    :class="[`alert-${alertLevel}`, { dragging: isDragging }]"
    draggable="true"
    @dragstart="onDragStart"
    @dragend="onDragEnd"
    @click="goToDetail"
  >
    <div class="card-header">
      <span class="card-name text-truncate">{{ customer.name }}</span>
      <AlertBadge
        v-if="customer.alert_level"
        :level="customer.alert_level"
        :days="customer.stay_days"
        :showDays="true"
      />
    </div>
    <div class="card-body">
      <div class="card-info-row">
        <el-icon :size="12"><User /></el-icon>
        <span class="text-truncate">{{ customer.contact_person || '-' }}</span>
      </div>
      <div class="card-info-row">
        <el-icon :size="12"><Location /></el-icon>
        <span class="text-truncate">{{ customer.region || '-' }}</span>
      </div>
      <div class="card-info-row">
        <el-icon :size="12"><Avatar /></el-icon>
        <span class="text-truncate">{{ customer.sales_name || '-' }}</span>
      </div>
    </div>
    <div class="card-footer">
      <span v-if="customer.contract_amount" class="card-amount">
        ¥{{ formatAmount(customer.contract_amount) }}
      </span>
      <span class="card-days">
        <el-icon :size="10"><Clock /></el-icon>
        {{ customer.stay_days || 0 }}d
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { User, Location, Avatar, Clock } from '@element-plus/icons-vue'
import AlertBadge from '@/components/AlertBadge.vue'

const props = defineProps({
  customer: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['drag-start', 'drag-end'])
const router = useRouter()
const isDragging = ref(false)

const alertLevel = computed(() => props.customer.alert_level || 'normal')

function formatAmount(val) {
  if (val === null || val === undefined || val === '') return '0'
  const num = Number(val)
  if (isNaN(num)) return '0'
  return num.toLocaleString()
}

function onDragStart(e) {
  isDragging.value = true
  e.dataTransfer.setData('text/plain', JSON.stringify({
    customerId: props.customer.id,
    currentStage: props.customer.stage
  }))
  e.dataTransfer.effectAllowed = 'move'
  emit('drag-start', props.customer)
}

function onDragEnd() {
  isDragging.value = false
  emit('drag-end', props.customer)
}

function goToDetail() {
  router.push(`/customer/${props.customer.id}`)
}
</script>

<style scoped>
.customer-card {
  background: var(--bg-white, #fff);
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  user-select: none;
  transition: box-shadow 0.2s, transform 0.2s;
  border-left: 3px solid var(--alert-normal, #52C41A);
  position: relative;
}

.customer-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.customer-card.dragging {
  opacity: 0.4;
  transform: rotate(2deg);
}

.customer-card.alert-warning {
  border-left-color: var(--alert-warning, #FAAD14);
  background: #fffbe6;
}

.customer-card.alert-danger {
  border-left-color: var(--alert-danger, #FF4D4F);
  background: #fff2f0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  flex: 1;
  min-width: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.card-info-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.card-info-row .text-truncate {
  flex: 1;
  min-width: 0;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 6px;
  border-top: 1px solid #f2f3f5;
}

.card-amount {
  font-size: 12px;
  font-weight: 600;
  color: #e6a23c;
}

.card-days {
  font-size: 11px;
  color: #c0c4cc;
  display: flex;
  align-items: center;
  gap: 2px;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
