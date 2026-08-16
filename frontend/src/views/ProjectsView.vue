<template>
  <div class="projects-page">
    <WorkspaceTopbar
      :user="auth.user"
      @logout="logout"
      @projects="load"
      @settings="settingsOpen = true"
    />
    <main class="projects-main">
      <header class="page-header">
        <div>
          <span class="eyebrow">项目知识库</span>
          <h1>选择工作项目</h1>
          <p>进入项目后，检索范围将锁定在该项目资料内。</p>
        </div>
        <el-button type="primary" @click="dialog = true">
          <el-icon><Plus /></el-icon>
          新建项目
        </el-button>
      </header>

      <div class="project-toolbar">
        <ProjectQuickSearch v-model="query" @select="openSuggestedProject" />
        <span>{{ filteredProjects.length }} 个可访问项目</span>
      </div>

      <section v-if="recentProjects.length" class="recent-section">
        <div class="section-title">最近访问</div>
        <div class="recent-list">
          <button v-for="project in recentProjects" :key="project.project_id" type="button" @click="enterProject(project)">
            <span class="project-symbol"><el-icon><FolderOpened /></el-icon></span>
            <span>{{ project.name }}</span>
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
      </section>

      <section class="all-projects">
        <div class="section-title">全部项目</div>
        <div class="project-list">
          <article v-for="project in filteredProjects" :key="project.project_id" class="project-row">
            <span class="project-symbol"><el-icon><Folder /></el-icon></span>
            <div class="project-copy">
              <strong>{{ project.name }}</strong>
              <span>{{ project.description || '暂无项目描述' }}</span>
            </div>
            <time>{{ formatDate(project.created_at) }}</time>
            <el-button type="primary" plain @click="enterProject(project)">
              进入工作台
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </article>
        </div>
        <el-empty v-if="!filteredProjects.length" description="没有匹配的项目" />
      </section>
    </main>

    <el-dialog v-model="dialog" title="新建项目" width="460px">
      <el-form label-position="top" @submit.prevent="create">
        <el-form-item label="项目名称" required><el-input v-model="name" maxlength="128" /></el-form-item>
        <el-form-item label="项目描述"><el-input v-model="description" type="textarea" :rows="3" maxlength="512" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" :disabled="!name.trim()" @click="create">创建并进入</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="settingsOpen" title="工作台设置" size="380px">
      <div class="setting-row">
        <div><strong>紧凑模式</strong><span>缩小工作台信息间距</span></div>
        <el-switch v-model="compactMode" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, Folder, FolderOpened, Plus } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import ProjectQuickSearch from '../components/ProjectQuickSearch.vue'
import WorkspaceTopbar from '../components/WorkspaceTopbar.vue'
import { request } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const projects = ref([])
const query = ref('')
const dialog = ref(false)
const settingsOpen = ref(false)
const creating = ref(false)
const name = ref('')
const description = ref('')

const filteredProjects = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return projects.value.filter(project => !keyword ||
    project.name.toLowerCase().includes(keyword) ||
    (project.description || '').toLowerCase().includes(keyword))
})
const recentProjects = computed(() => workspace.recentProjectIds
  .map(id => projects.value.find(project => project.project_id === id))
  .filter(Boolean)
  .slice(0, 4))
const compactMode = computed({
  get: () => workspace.compactMode,
  set: value => workspace.setCompactMode(value)
})

async function load() {
  try {
    const data = await request('GET', '/projects')
    projects.value = data.items
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function create() {
  if (!name.value.trim() || creating.value) return
  creating.value = true
  try {
    const project = await request('POST', '/projects', {
      name: name.value.trim(), description: description.value.trim()
    })
    dialog.value = false
    name.value = ''
    description.value = ''
    enterProject(project)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    creating.value = false
  }
}

function enterProject(project) {
  workspace.rememberProject(project.project_id)
  router.push('/projects/' + project.project_id)
}

function openSuggestedProject(project) {
  workspace.rememberProject(project.project_id)
  router.push({ path: '/projects/' + project.project_id,
                query: { library: '1' } })
}

function formatDate(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value))
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(load)
</script>

<style scoped>
.projects-page { min-height: 100vh; background: #f2f4f7; color: #263445; }
.projects-main { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 38px 0 64px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding-bottom: 24px; border-bottom: 1px solid #d9dee5; }
.eyebrow { color: #1f5fbf; font-size: 11px; font-weight: 700; }
.page-header h1 { margin: 5px 0 0; font-size: 26px; letter-spacing: 0; }
.page-header p { margin: 8px 0 0; color: #687586; font-size: 13px; }
.project-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 22px 0 14px; }
.project-toolbar :deep(.el-input) { width: min(420px, 100%); }
.project-toolbar > span { color: #7a8594; font-size: 12px; }
.section-title { margin-bottom: 10px; color: #667085; font-size: 12px; font-weight: 600; }
.recent-section { margin-top: 10px; }
.recent-list { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.recent-list button { min-width: 0; height: 54px; display: flex; align-items: center; gap: 9px; padding: 0 12px; border: 1px solid #d7dde5; border-radius: 6px; background: #fff; color: #344054; cursor: pointer; }
.recent-list button:hover { border-color: #83a3ce; }
.recent-list button > span:nth-child(2) { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left; }
.project-symbol { width: 30px; height: 30px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 5px; background: #e8eef7; color: #1f5fbf; }
.all-projects { margin-top: 28px; }
.project-list { border-top: 1px solid #d9dee5; }
.project-row { display: grid; grid-template-columns: 40px minmax(0, 1fr) 110px auto; align-items: center; gap: 14px; min-height: 76px; padding: 10px 12px; border-bottom: 1px solid #dfe3e8; background: #fff; }
.project-copy { min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.project-copy strong, .project-copy span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-copy strong { font-size: 14px; }
.project-copy span, .project-row time { color: #7a8594; font-size: 12px; }
.setting-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 16px 0; border-bottom: 1px solid #e5e8ec; }
.setting-row > div { display: flex; flex-direction: column; gap: 5px; }
.setting-row strong { font-size: 13px; }
.setting-row span { color: #7a8594; font-size: 11px; }
@media (max-width: 900px) {
  .recent-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .project-row { grid-template-columns: 40px minmax(0, 1fr) auto; }
  .project-row time { display: none; }
}
@media (max-width: 600px) {
  .projects-main { width: calc(100% - 24px); padding-top: 22px; }
  .page-header { align-items: flex-start; flex-direction: column; }
  .project-toolbar { align-items: flex-start; flex-direction: column; }
  .recent-list { grid-template-columns: 1fr; }
  .project-row { grid-template-columns: 34px minmax(0, 1fr); }
  .project-row > .el-button { grid-column: 1 / -1; }
}
</style>
