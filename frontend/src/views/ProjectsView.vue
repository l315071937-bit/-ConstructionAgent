<template>
  <div class="wrap">
    <el-header class="head">
      <span class="title">ConstructionAgent</span>
      <div>
        <span class="who">{{ auth.user && auth.user.username }}</span>
        <el-button size="small" @click="auth.logout(); $router.push('/login')">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <div class="bar">
        <h3>我的项目</h3>
        <el-button type="primary" @click="dialog = true">新建项目</el-button>
      </div>
      <el-row :gutter="16">
        <el-col v-for="p in projects" :key="p.project_id" :span="6">
          <el-card class="proj" @click="$router.push('/projects/' + p.project_id)">
            <div class="pname">{{ p.name }}</div>
            <div class="pdesc">{{ p.description || '暂无描述' }}</div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!projects.length" description="还没有项目" />
    </el-main>
    <el-dialog v-model="dialog" title="新建项目" width="420px">
      <el-form>
        <el-form-item label="名称"><el-input v-model="name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="desc" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { request } from '../api/client'

const auth = useAuthStore()
const projects = ref([])
const dialog = ref(false)
const name = ref('')
const desc = ref('')

async function load() {
  const data = await request('GET', '/projects')
  projects.value = data.items
}
async function create() {
  await request('POST', '/projects', { name: name.value, description: desc.value })
  dialog.value = false
  name.value = ''
  desc.value = ''
  await load()
}
onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.who { margin-right: 12px; color: #606266; }
.bar { display: flex; justify-content: space-between; align-items: center; }
.proj { cursor: pointer; margin-bottom: 16px; }
.pname { font-weight: 600; }
.pdesc { color: #909399; font-size: 13px; margin-top: 8px; }
</style>
