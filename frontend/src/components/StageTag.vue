<template>
  <span
    class="stage-tag"
    :class="[`stage-tag--${size}`, `stage-color-${stage}`, `stage-bg-${stage}`]"
  >
    {{ stageName }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stage: {
    type: Number,
    required: true,
    validator: (val) => val >= 1 && val <= 8
  },
  size: {
    type: String,
    default: 'default',
    validator: (val) => ['small', 'default', 'large'].includes(val)
  }
})

const STAGE_NAMES = {
  1: 'Lead',
  2: 'Consult',
  3: 'Contract',
  4: 'Requirements',
  5: 'Service',
  6: 'Delivery',
  7: 'Payment',
  8: 'Completed'
}

const stageName = computed(() => STAGE_NAMES[props.stage] || 'Unknown')
</script>

<style scoped>
.stage-tag {
  display: inline-flex;
  align-items: center;
  font-weight: 500;
  border-radius: 4px;
  white-space: nowrap;
}

.stage-tag--small {
  font-size: 11px;
  padding: 1px 6px;
}

.stage-tag--default {
  font-size: 12px;
  padding: 2px 8px;
}

.stage-tag--large {
  font-size: 14px;
  padding: 4px 12px;
}
</style>
