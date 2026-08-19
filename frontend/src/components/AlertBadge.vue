<template>
  <span
    v-if="level && level !== 'normal'"
    class="alert-badge"
    :class="`alert-badge--${level}`"
  >
    <el-icon v-if="level === 'warning'" :size="12"><WarningFilled /></el-icon>
    <el-icon v-if="level === 'danger'" :size="12"><CircleCloseFilled /></el-icon>
    <span v-if="showDays && days !== undefined">{{ days }}d</span>
    <span v-else>{{ levelText }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: {
    type: String,
    default: 'normal',
    validator: (val) => ['normal', 'warning', 'danger'].includes(val)
  },
  days: {
    type: Number,
    default: undefined
  },
  showDays: {
    type: Boolean,
    default: false
  }
})

const levelText = computed(() => {
  const map = { normal: 'Normal', warning: 'Warning', danger: 'Overdue' }
  return map[props.level] || 'Normal'
})
</script>

<style scoped>
.alert-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 3px;
}

.alert-badge--warning {
  color: #e6a23c;
  background: #fdf6ec;
}

.alert-badge--danger {
  color: #f56c6c;
  background: #fef0f0;
}
</style>
