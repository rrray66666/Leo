<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Today's Follow-ups</h2>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">New Reminder</el-button>
    </div>

    <div class="followup-list" v-loading="loading">
      <div
        v-for="item in followups"
        :key="item.id"
        class="followup-card"
        :class="{ 'is-done': item.is_done }"
      >
        <div class="followup-left">
          <el-checkbox
            :model-value="item.is_done"
            @change="handleToggleDone(item)"
          />
        </div>
        <div class="followup-main">
          <div class="followup-header">
            <span class="followup-title" :class="{ 'line-through': item.is_done }">
              {{ item.title }}
            </span>
            <div class="followup-tags">
            <StageTag v-if="item.stage" :stage="item.stage" size="small" />
            <el-tag v-if="item.remind_type === 'high_priority'" type="danger" size="small">High Priority</el-tag>
          </div>
        </div>
        <div class="followup-body">
          <span v-if="item.customer_id" class="followup-customer">
            <el-link type="primary" @click="$router.push(`/customer/${item.customer_id}`)">
              View Customer
            </el-link>
          </span>
          <span class="followup-desc">{{ item.content || '' }}</span>
        </div>
        <div class="followup-footer">
          <span class="followup-time">
            <el-icon :size="12"><Clock /></el-icon>
            {{ item.remind_at ? new Date(item.remind_at).toLocaleString() : '' }}
          </span>
          <div class="followup-actions">
              <el-button link type="primary" size="small" @click="handleEdit(item)">Edit</el-button>
              <el-popconfirm title="Confirm delete?" @confirm="handleDelete(item.id)">
                <template #reference>
                  <el-button link type="danger" size="small">Delete</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-if="followups.length === 0" description="No follow-ups for today" />
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingItem ? 'Edit Reminder' : 'New Reminder'"
      width="500px"
    >
      <el-form :model="form" label-width="80px">
        <el-form-item label="Title" prop="title" required>
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="Content (optional)">
          <el-input v-model="form.content" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="Related Customer" required>
          <el-select v-model="form.customer_id" filterable remote placeholder="Search customer"
            :remote-method="searchCustomers" style="width:100%">
            <el-option v-for="c in customerOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Remind Time (optional)">
          <el-date-picker v-model="form.remind_at" type="datetime" placeholder="Select time" style="width:100%" />
        </el-form-item>
        <el-form-item label="Priority (optional)">
          <el-select v-model="form.remind_type" style="width:100%">
            <el-option label="Normal" value="system_notification" />
            <el-option label="High" value="high_priority" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">Save</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { followUpApi, customerApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Plus, Clock } from '@element-plus/icons-vue'
import StageTag from '@/components/StageTag.vue'

const loading = ref(false)
const saving = ref(false)
const followups = ref([])
const showCreateDialog = ref(false)
const editingItem = ref(null)
const customerOptions = ref([])

const form = reactive({
  title: '', content: '', customer_id: null, remind_at: '', remind_type: 'system_notification'
})

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const res = await followUpApi.todayList()
    followups.value = res.data || res || []
  } catch {
    followups.value = []
  } finally {
    loading.value = false
  }
}

async function searchCustomers(query) {
  if (!query) return
  try {
    const res = await customerApi.list({ keyword: query, page_size: 10 })
    const data = res.data?.items || res.data || []
    customerOptions.value = data
  } catch {
    customerOptions.value = []
  }
}

function resetForm() {
  form.title = ''
  form.content = ''
  form.customer_id = null
  form.remind_at = ''
  form.remind_type = 'system_notification'
  editingItem.value = null
}

function handleEdit(item) {
  editingItem.value = item
  form.title = item.title
  form.content = item.content || ''
  form.customer_id = item.customer_id
  form.remind_at = item.remind_at || ''
  form.remind_type = item.remind_type || 'system_notification'
  showCreateDialog.value = true
}

async function handleSave() {
  if (!form.title) {
    ElMessage.warning('Please enter a title')
    return
  }
  if (!form.customer_id) {
    ElMessage.warning('Please select a related customer')
    return
  }
  saving.value = true
  try {
    const payload = {
      title: form.title,
      content: form.content,
      remind_at: form.remind_at || null,
      remind_type: form.remind_type
    }
    if (editingItem.value) {
      await followUpApi.update(editingItem.value.id, payload)
      ElMessage.success('Updated')
    } else {
      await followUpApi.create({ ...payload, customer_id: form.customer_id })
      ElMessage.success('Created')
    }
    showCreateDialog.value = false
    resetForm()
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Save failed')
  } finally {
    saving.value = false
  }
}

async function handleToggleDone(item) {
  try {
    if (item.is_done) return
    await followUpApi.markDone(item.id)
    item.is_done = true
    ElMessage.success('Marked as done')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Operation failed')
  }
}

async function handleDelete(id) {
  try {
    await followUpApi.delete(id)
    ElMessage.success('Deleted')
    await loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Delete failed')
  }
}
</script>

<style scoped>
.followup-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.followup-card {
  display: flex;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s;
}

.followup-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.followup-card.is-done {
  opacity: 0.6;
}

.followup-left {
  padding-right: 12px;
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.followup-main {
  flex: 1;
  min-width: 0;
}

.followup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.followup-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.followup-title.line-through {
  text-decoration: line-through;
  color: #909399;
}

.followup-tags {
  display: flex;
  gap: 4px;
}

.followup-body {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.followup-customer {
  flex-shrink: 0;
}

.followup-desc {
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.followup-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #909399;
}

.followup-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.followup-actions {
  margin-left: auto;
}
</style>
