<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Right } from '@element-plus/icons-vue'
import { api } from '../api'
import { setAdminToken } from '../lib/auth'

const router = useRouter()
const form = reactive({ password: '' })
const loading = ref(false)

async function submit() {
  if (!form.password.trim()) {
    ElMessage.warning('请输入管理员密码')
    return
  }
  loading.value = true
  try {
    const result = await api.admin.login(form.password)
    setAdminToken(result.access_token)
    ElMessage.success('登录成功')
    await router.replace({ name: 'admin-dashboard' })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="center-page">
    <div class="login-panel">
      <div class="brand-mark">YIYIN-PANEL</div>
      <h1>管理后台登录</h1>
      <p class="muted-text">访问路径为 <code>/yiyin/admin</code>，认证成功后进入开关管理页。</p>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input
            v-model="form.password"
            show-password
            size="large"
            placeholder="请输入管理员密码"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="full-width" :loading="loading" @click="submit" :icon="Right">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>
