<template>
  <div class="page-container">
    <div class="page-header">
      <h2>Profile</h2>
    </div>

    <el-row :gutter="24">
      <el-col :span="12">
        <!-- Personal Info -->
        <div class="detail-section">
          <h3>Personal Info</h3>
          <el-form :model="profileForm" label-width="100px" ref="profileFormRef">
            <el-form-item label="Name" prop="name">
              <el-input v-model="profileForm.name" />
            </el-form-item>
            <el-form-item label="Email">
              <el-input v-model="profileForm.email" disabled />
            </el-form-item>
            <el-form-item label="Phone">
              <el-input v-model="profileForm.phone" />
            </el-form-item>
            <el-form-item label="Role">
              <el-input :value="profileForm.role === 'admin' ? 'Admin' : 'Sales'" disabled />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveProfile">Save Changes</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :span="12">
        <!-- Change Password -->
        <div class="detail-section">
          <h3>Change Password</h3>
          <el-form :model="pwdForm" label-width="100px" ref="pwdFormRef" :rules="pwdRules">
            <el-form-item label="Current Password" prop="old_password">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="New Password" prop="new_password">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="Confirm Password" prop="confirm">
              <el-input v-model="pwdForm.confirm" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="resetting" @click="handleResetPwd">Change Password</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const saving = ref(false)
const resetting = ref(false)
const profileFormRef = ref(null)
const pwdFormRef = ref(null)

const profileForm = reactive({
  name: '',
  email: '',
  phone: '',
  role: ''
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm: ''
})

const pwdRules = {
  old_password: [{ required: true, message: 'Please enter current password', trigger: 'blur' }],
  new_password: [
    { required: true, message: 'Please enter new password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ],
  confirm: [
    { required: true, message: 'Please confirm new password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== pwdForm.new_password) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

onMounted(() => {
  const info = userStore.userInfo
  if (info) {
    profileForm.name = info.name || ''
    profileForm.email = info.email || ''
    profileForm.phone = info.phone || ''
    profileForm.role = info.role || ''
  }
})

async function handleSaveProfile() {
  if (!profileForm.name) {
    ElMessage.warning('Please enter name')
    return
  }
  saving.value = true
  try {
    await userStore.updateProfile({
      name: profileForm.name,
      phone: profileForm.phone
    })
    ElMessage.success('Profile updated')
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Update failed')
  } finally {
    saving.value = false
  }
}

async function handleResetPwd() {
  if (!pwdFormRef.value) return
  try {
    await pwdFormRef.value.validate()
  } catch {
    return
  }
  resetting.value = true
  try {
    await userStore.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('Password changed')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.message || 'Password change failed')
  } finally {
    resetting.value = false
  }
}
</script>
