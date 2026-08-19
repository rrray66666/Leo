<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Data Dictionary</h2>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="Industries" name="industries">
        <div class="section-toolbar">
          <el-button size="small" type="primary" :icon="Plus" @click="addItem('industries')">New Industry</el-button>
        </div>
        <el-table :data="dictData.industries" stripe size="small">
          <el-table-column type="index" label="Sort" width="60" />
          <el-table-column prop="name" label="Name" min-width="150" />
          <el-table-column prop="code" label="Code" width="120" />
          <el-table-column label="Actions" width="150">
            <template #default="{ row, $index }">
              <el-button link type="primary" size="small" @click="editItem('industries', row, $index)">Edit</el-button>
              <el-popconfirm title="Confirm deletion?" @confirm="deleteItem('industries', $index)">
                <template #reference>
                  <el-button link type="danger" size="small">Delete</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Regions" name="regions">
        <div class="section-toolbar">
          <el-button size="small" type="primary" :icon="Plus" @click="addItem('regions')">New Region</el-button>
        </div>
        <el-table :data="dictData.regions" stripe size="small">
          <el-table-column type="index" label="Sort" width="60" />
          <el-table-column prop="name" label="Name" min-width="150" />
          <el-table-column prop="code" label="Code" width="120" />
          <el-table-column label="Actions" width="150">
            <template #default="{ row, $index }">
              <el-button link type="primary" size="small" @click="editItem('regions', row, $index)">Edit</el-button>
              <el-popconfirm title="Confirm deletion?" @confirm="deleteItem('regions', $index)">
                <template #reference>
                  <el-button link type="danger" size="small">Delete</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Channels" name="channels">
        <div class="section-toolbar">
          <el-button size="small" type="primary" :icon="Plus" @click="addItem('channels')">New Channel</el-button>
        </div>
        <el-table :data="dictData.channels" stripe size="small">
          <el-table-column type="index" label="Sort" width="60" />
          <el-table-column prop="name" label="Name" min-width="150" />
          <el-table-column prop="code" label="Code" width="120" />
          <el-table-column label="Actions" width="150">
            <template #default="{ row, $index }">
              <el-button link type="primary" size="small" @click="editItem('channels', row, $index)">Edit</el-button>
              <el-popconfirm title="Confirm deletion?" @confirm="deleteItem('channels', $index)">
                <template #reference>
                  <el-button link type="danger" size="small">Delete</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Categories" name="categories">
        <div class="section-toolbar">
          <el-button size="small" type="primary" :icon="Plus" @click="addItem('categories')">New Category</el-button>
        </div>
        <el-table :data="dictData.categories" stripe size="small">
          <el-table-column type="index" label="Sort" width="60" />
          <el-table-column prop="name" label="Name" min-width="150" />
          <el-table-column prop="code" label="Code" width="120" />
          <el-table-column label="Actions" width="150">
            <template #default="{ row, $index }">
              <el-button link type="primary" size="small" @click="editItem('categories', row, $index)">Edit</el-button>
              <el-popconfirm title="Confirm deletion?" @confirm="deleteItem('categories', $index)">
                <template #reference>
                  <el-button link type="danger" size="small">Delete</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isNew ? 'New' : 'Edit'"
      width="400px"
    >
      <el-form :model="dialog.form" label-width="60px">
        <el-form-item label="Name">
          <el-input v-model="dialog.form.name" />
        </el-form-item>
        <el-form-item label="Code">
          <el-input v-model="dialog.form.code" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmDialog">Confirm</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { dictApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const activeTab = ref('industries')
const dictData = reactive({
  industries: [],
  regions: [],
  channels: [],
  categories: []
})

const dialog = reactive({
  visible: false,
  isNew: true,
  type: '',
  index: -1,
  form: { name: '', code: '' }
})

onMounted(() => loadAllDicts())

async function loadAllDicts() {
  try {
    const [ind, reg, ch, cat] = await Promise.all([
      dictApi.getIndustries(),
      dictApi.getRegions(),
      dictApi.getChannels(),
      dictApi.getCategories()
    ])
    dictData.industries = ind.data || ind || []
    dictData.regions = reg.data || reg || []
    dictData.channels = ch.data || ch || []
    dictData.categories = cat.data || cat || []
  } catch {
    ElMessage.error('Failed to load dictionary')
  }
}

function addItem(type) {
  dialog.isNew = true
  dialog.type = type
  dialog.form = { name: '', code: '' }
  dialog.visible = true
}

function editItem(type, row, index) {
  dialog.isNew = false
  dialog.type = type
  dialog.index = index
  dialog.form = { name: row.name, code: row.code }
  dialog.visible = true
}

async function confirmDialog() {
  const { type, isNew, index, form } = dialog
  if (!form.name) {
    ElMessage.warning('Please enter name')
    return
  }
  if (isNew) {
    dictData[type].push({ name: form.name, code: form.code || form.name })
  } else {
    dictData[type][index] = { name: form.name, code: form.code || form.name }
  }
  // Save to server
  try {
    await dictApi[`update${capitalize(type)}`](dictData[type])
    ElMessage.success(isNew ? 'Created' : 'Updated')
    dialog.visible = false
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Save failed')
    // Reload
    await loadAllDicts()
  }
}

function deleteItem(type, index) {
  dictData[type].splice(index, 1)
  dictApi[`update${capitalize(type)}`](dictData[type]).then(() => {
    ElMessage.success('Deleted')
  }).catch(() => {
    loadAllDicts()
  })
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1)
}
</script>

<style scoped>
.section-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

:deep(.el-tabs__content) {
  overflow: visible;
}
</style>
