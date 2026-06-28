<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <span class="logo">墨</span>
        <h1>墨写</h1>
        <p>AI 驱动的中文自媒体写作平台</p>
      </div>
      <el-tabs v-model="tab">
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" @submit.prevent="handleLogin">
            <el-form-item>
              <el-input v-model="loginForm.email" placeholder="邮箱" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password />
            </el-form-item>
            <el-button type="primary" size="large" style="width:100%" :loading="loading" native-type="submit">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form :model="regForm" @submit.prevent="handleRegister">
            <el-form-item>
              <el-input v-model="regForm.display_name" placeholder="昵称（可选）" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.email" placeholder="邮箱" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input v-model="regForm.password" type="password" placeholder="密码（至少6位）" size="large" show-password />
            </el-form-item>
            <el-button type="primary" size="large" style="width:100%" :loading="loading" native-type="submit">
              注册并开始写作
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <p class="hint">注册后自动创建 Tactile 写作空间与 AI 写作助手</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api/client'

const router = useRouter()
const tab = ref('login')
const loading = ref(false)
const loginForm = ref({ email: '', password: '' })
const regForm = ref({ email: '', password: '', display_name: '' })

async function handleLogin() {
  loading.value = true
  try {
    const { data } = await api.post('/auth/login', loginForm.value)
    localStorage.setItem('token', data.token)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    const { data } = await api.post('/auth/register', regForm.value)
    localStorage.setItem('token', data.token)
    ElMessage.success('注册成功，写作助手已就绪')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.login-header { text-align: center; margin-bottom: 24px; }
.login-header .logo {
  display: inline-flex;
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  border-radius: 12px;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 12px;
}
.login-header h1 { font-size: 28px; margin-bottom: 4px; }
.login-header p { color: #909399; font-size: 14px; }
.hint { text-align: center; color: #c0c4cc; font-size: 12px; margin-top: 16px; }
</style>
