<template>
  <main class="entry-state">
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在进入工作台</span>
    </div>
    <el-result v-else-if="error" icon="error" title="无法进入工作台" :sub-title="error">
      <template #extra><el-button type="primary" @click="load">重试</el-button></template>
    </el-result>
    <div v-else-if="!projects.length" class="empty-state">
      <h1>创建第一个工作项目</h1>
      <el-input v-model="name" maxlength="128" placeholder="项目名称" @keydown.enter="createProject" />
      <el-input v-model="description" type="textarea" :rows="3" maxlength="512" placeholder="项目描述（可选）" />
      <el-button type="primary" :loading="creating" :disabled="!name.trim()" @click="createProject">
        创建并进入三栏工作台
      </el-button>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { request } from '../api/client'
import { useWorkspaceStore } from '../stores/workspace'

const router = useRouter()
const workspace = useWorkspaceStore()
const loading = ref(true)
const creating = ref(false)
const projects = ref([])
const name = ref('')
const description = ref('')
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await request('GET', '/projects')
    projects.value = data.items || []
    const recent = workspace.recentProjectIds
      .map(id => projects.value.find(project => project.project_id === id))
      .find(Boolean)
    const target = recent || projects.value[0]
    if (target) {
      workspace.rememberProject(target.project_id)
      await router.replace('/projects/' + target.project_id)
    }
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}

async function createProject() {
  if (!name.value.trim() || creating.value) return
  creating.value = true
  try {
    const project = await request('POST', '/projects', {
      name: name.value.trim(), description: description.value.trim()
    })
    workspace.rememberProject(project.project_id)
    await router.replace('/projects/' + project.project_id)
  } catch (requestError) {
    ElMessage.error(requestError.message)
  } finally {
    creating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.entry-state { min-height: 100vh; display: grid; place-items: center; padding: 24px; background: #f3f5f8; color: #263445; }
.loading-state { display: flex; align-items: center; gap: 10px; color: #667085; font-size: 13px; }
.loading-state .el-icon { color: #2166d1; font-size: 20px; }
.empty-state { width: min(420px, 100%); display: flex; flex-direction: column; gap: 12px; }
.empty-state h1 { margin: 0 0 8px; font-size: 20px; letter-spacing: 0; }
</style>
