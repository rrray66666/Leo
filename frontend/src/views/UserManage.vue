<template>
  <div class="page-container">
    <div class="page-header">
      <h2>User Management</h2>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">New User</el-button>
    </div>

    <el-table :data="userList" v-loading="loading" stripe>
      <el-table-column prop="name" label="Name" width="120" />
      <el-table-column prop="email" label="Email" width="220" />
      <el-table-column prop="role" label="Role" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
            {{ row.role === 'admin' ? 'Admin' : 'Sales' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="Phone" width="140" />
      <el-table-column prop="is_active" label="Status" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? 'Active' : 'Disabled' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created At" width="160" />
      <el-table-column label="Actions" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">Edit</el-button>
          <el-button link type="primary" @click="handleResetPwd(row)">Reset Password</el-button>
          <el-button
            link
            :type="row.is_active ? 'warning' : 'success'"
            @click="handleToggleActive(row)"
          >
            {{ row.is_active ? 'Disable' : 'Enable' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create User Dialog -->
    <el-dialog v-model="showCreateDialog" title="New User" width="500px">
      <el-form :model="createForm" label-width="80px" ref="createFormRef" :rules="createRules">
        <el-form-item label="Name" prop="name">
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Phone (optional)">
          <el-input v-model="createForm.phone" />
        </el-form-item>
        <el-form-item label="Role (optional, defaults to Sales)">
          <el-select v-model="createForm.role" style="width:100%">
            <el-option label="Admin" value="admin" />
            <el-option label="Sales" value="sales" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button>
      </template>
    </el-dialog>

    <!-- Edit User Dialog -->
    <el-dialog v-model="showEditDialog" title="Edit User" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="Name" required>
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="Phone (optional)">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="Role (optional)">
          <el-select v-model="editForm.role" style="width:100%">
            <el-option label="Admin" value="admin" />
            <el-option label="Sales" value="sales" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="editing" @click="confirmEdit">Save</el-button>
      </template>
    </el-dialog>

    <!-- Reset Password Dialog -->
    <el-dialog v-model="showPwdDialog" title="Reset Password" width="400px">
      <el-form :model="pwdForm" label-width="100px">
        <el-form-item label="New Password" required>
          <el-input v-model="pwdForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="Confirm Password" required>
          <el-input v-model="pwdForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPwdDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="resetting" @click="confirmResetPwd">Confirm Reset</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { userApi } from '@/api'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const creating = ref(false)
const editing = ref(false)
const resetting = ref(false)
const userList = ref([])

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showPwdDialog = ref(false)
const currentEditId = ref(null)
const currentPwdId = ref(null)
const createFormRef = ref(null)

const createForm = reactive({
  name: '', email: '', password: '', phone: '', role: 'sales'
})

const createRules = {
  name: [{ required: true, message: 'Please enter name', trigger: 'blur' }],
  email: [{ required: true, message: 'Please enter email', trigger: 'blur' }, { type: 'email', message: 'Invalid email format', trigger: 'blur' }],
  password: [{ required: true, message: 'Please enter password', trigger: 'blur' }, { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }]
}

const editForm = reactive({ name: '', phone: '', role: 'sales' })
const pwdForm = reactive({ password: '', confirm: '' })

onMounted(() => loadUsers())

async function loadUsers() {
  loading.value = true
  try {
    const res = await userApi.list()
    userList.value = res.data?.items || res.data || []
  } catch {
    userList.value = []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch { return }
  creating.value = true
  try {
    await userApi.create(createForm)
    ElMessage.success('Created')
    showCreateDialog.value = false
    createForm.name = ''; createForm.email = ''; createForm.password = ''; createForm.phone = ''; createForm.role = 'sales'
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Create failed')
  } finally {
    creating.value = false
  }
}

function handleEdit(row) {
  currentEditId.value = row.id
  editForm.name = row.name
  editForm.phone = row.phone || ''
  editForm.role = row.role
  showEditDialog.value = true
}

async function confirmEdit() {
  editing.value = true
  try {
    await userApi.update(currentEditId.value, editForm)
    ElMessage.success('Updated')
    showEditDialog.value = false
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Update failed')
  } finally {
    editing.value = false
  }
}

function handleResetPwd(row) {
  currentPwdId.value = row.id
  pwdForm.password = ''
  pwdForm.confirm = ''
  showPwdDialog.value = true
}

async function confirmResetPwd() {
  if (pwdForm.password !== pwdForm.confirm) {
    ElMessage.warning('Passwords do not match')
    return
  }
  if (pwdForm.password.length < 6) {
    ElMessage.warning('Password must be at least 6 characters')
    return
  }
  resetting.value = true
  try {
    await userApi.resetPassword(currentPwdId.value, { new_password: pwdForm.password })
    ElMessage.success('Password reset successful')
    showPwdDialog.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Reset failed')
  } finally {
    resetting.value = false
  }
}

async function handleToggleActive(row) {
  try {
    await userApi.update(row.id, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? 'Disabled' : 'Enabled')
    await loadUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Operation failed')
  }
}
</script>
