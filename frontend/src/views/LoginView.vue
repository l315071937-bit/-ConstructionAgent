<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h2>ConstructionAgent</h2>
      <p class="sub">建筑工程智能助手</p>
      <el-form @submit.prevent="doLogin">
        <el-form-item><el-input v-model="username" placeholder="用户名" /></el-form-item>
        <el-form-item><el-input v-model="password" type="password" placeholder="密码" show-password /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
      </el-form>
      <p v-if="error" class="err">{{ error }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { request } from '../api/client'

const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function doLogin() {
  loading.value = true
  error.value = ''
  try {
    const data = await request('POST', '/auth/login', { username: username.value, password: password.value })
    auth.setLogin(data.access_token, data.user)
    router.push('/projects')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: #f5f7fa; }
.login-card { width: 360px; text-align: center; }
.sub { color: #909399; margin-bottom: 20px; }
.err { color: #f56c6c; margin-top: 10px; }
</style>
