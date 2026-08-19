<template>
  <el-autocomplete
    v-model="searchText"
    :fetch-suggestions="handleSearch"
    :trigger-on-focus="false"
    placeholder="Search customers..."
    :debounce="300"
    clearable
    size="default"
    class="global-search"
    @select="handleSelect"
  >
    <template #prefix>
      <el-icon><Search /></el-icon>
    </template>
    <template #default="{ item }">
      <div class="search-result-item" @click="handleSelect(item)">
        <div class="search-result-name">{{ item.label }}</div>
        <div class="search-result-info">
          <StageTag :stage="item.stage" size="small" />
          <span v-if="item.contact" class="search-result-contact">{{ item.contact }}</span>
        </div>
      </div>
    </template>
  </el-autocomplete>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { searchApi } from '@/api'
import StageTag from '@/components/StageTag.vue'

const router = useRouter()
const searchText = ref('')

async function handleSearch(queryString, cb) {
  if (!queryString || queryString.trim().length < 1) {
    cb([])
    return
  }
  try {
    const res = await searchApi.globalSearch({ keyword: queryString, page: 1, page_size: 8 })
    const data = (res.data && res.data.items) || res.data || []
    const items = Array.isArray(data) ? data : []
    const suggestions = items.map(item => ({
      value: item.name,
      label: item.name,
      id: item.id,
      stage: item.current_stage,
      contact: item.contact_person
    }))
    cb(suggestions)
  } catch {
    cb([])
  }
}

function handleSelect(item) {
  if (item && item.id) {
    router.push(`/customer/${item.id}`)
    searchText.value = ''
  }
}
</script>

<style scoped>
.global-search {
  width: 280px;
}

.search-result-item {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.search-result-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.search-result-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.search-result-contact {
  font-size: 12px;
  color: #909399;
}
</style>
