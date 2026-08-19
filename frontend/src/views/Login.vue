<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="40" color="#409EFF"><Management /></el-icon>
        <h2>CRM System</h2>
        <p class="login-subtitle">{{ mode === 'login' ? 'Please login to your account' : 'Create a new account' }}</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @keyup.enter="mode === 'login' ? handleLogin() : handleRegister()"
      >
        <el-form-item v-if="mode === 'register'" prop="name">
          <el-input
            v-model="form.name"
            placeholder="Name"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            placeholder="Email"
            :prefix-icon="Message"
            size="large"
          />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" prop="phone">
          <el-input
            v-model="form.phone"
            placeholder="Phone (optional)"
            :prefix-icon="Phone"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            placeholder="Password"
            type="password"
            show-password
            :prefix-icon="Lock"
            size="large"
          />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            placeholder="Confirm password"
            type="password"
            show-password
            :prefix-icon="Lock"
            size="large"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="mode === 'login' ? handleLogin() : handleRegister()"
          >
            {{ loading ? (mode === 'login' ? 'Logging in...' : 'Registering...') : (mode === 'login' ? 'Login' : 'Register') }}
          </el-button>
        </el-form-item>
        <div class="login-toggle">
          <span v-if="mode === 'login'">
            Don't have an account?
            <a class="toggle-link" @click="switchMode('register')">Register</a>
          </span>
          <span v-else>
            Already have an account?
            <a class="toggle-link" @click="switchMode('login')">Login</a>
          </span>
        </div>
      </el-form>
      <div v-if="errorMsg" class="login-error">
        {{ errorMsg }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Message, Lock, User, Phone } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const mode = ref('login')

const form = reactive({
  name: '',
  email: '',
  phone: '',
  password: '',
  confirm_password: ''
})

const rules = {
  name: [
    { required: true, message: 'Please enter name', trigger: 'blur' },
    { min: 2, max: 50, message: 'Name must be 2-50 characters', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'Please enter email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: 'blur' }
  ],
  phone: [
    { max: 20, message: 'Phone must be at most 20 characters', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: 'Please confirm password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function switchMode(next) {
  mode.value = next
  errorMsg.value = ''
  formRef.value?.clearValidate()
}

async function handleLogin() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    await userStore.login({
      email: form.email,
      password: form.password
    })
    ElMessage.success('Login successful')
    router.push('/')
  } catch (error) {
    errorMsg.value = error.response?.data?.detail || error.response?.data?.message || error.message || 'Login failed, please check email and password'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (form.password !== form.confirm_password) {
    errorMsg.value = 'Passwords do not match'
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    await userStore.register({
      name: form.name,
      email: form.email,
      phone: form.phone,
      password: form.password
    })
    ElMessage.success('Registration successful')
    router.push('/kanban')
  } catch (error) {
    errorMsg.value = error.response?.data?.detail || error.response?.data?.message || error.message || 'Registration failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h2 {
  margin-top: 12px;
  font-size: 22px;
  color: #303133;
}

.login-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}

.login-form {
  margin-top: 8px;
}

.login-btn {
  width: 100%;
  font-size: 16px;
}

.login-toggle {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: #909399;
}

.toggle-link {
  color: #409eff;
  cursor: pointer;
  margin-left: 4px;
}

.toggle-link:hover {
  text-decoration: underline;
}

.login-error {
  margin-top: 16px;
  padding: 8px 12px;
  background: #fef0f0;
  color: #f56c6c;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;
}
</style>
