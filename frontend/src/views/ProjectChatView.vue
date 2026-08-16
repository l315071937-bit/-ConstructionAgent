<template>
  <div class="workspace" :class="{ compact: compactMode }">
    <WorkspaceTopbar
      :user="auth.user"
      :project="currentProject"
      :evidence-count="evidences.length"
      @logout="logout"
      @open-evidence="openEvidencePanel"
      @open-navigation="navigationOpen = true"
      @projects="$router.push('/projects')"
      @settings="settingsOpen = true"
      @switch-project="projectPickerOpen = true"
    />

    <div class="workspace-body" :class="{ 'without-evidence': !evidenceVisible }">
      <WorkspaceSidebar
        class="desktop-navigation"
        :current-project="currentProject"
        :projects="projects"
        :session-title="sessionTitle"
        @new-chat="newConversation"
        @select-project="lockProject"
        @switch-project="projectPickerOpen = true"
      />

      <main class="conversation-panel">
        <header class="conversation-header">
          <div class="conversation-title">
            <span class="agent-label">项目资料检索</span>
            <h1>{{ currentProject ? currentProject.name : '项目工作台' }}</h1>
          </div>
          <div class="knowledge-status">
            <el-icon><Lock /></el-icon>
            <span>知识库已锁定</span>
            <strong>{{ readyDocumentCount }}/{{ documents.length }}</strong>
          </div>
        </header>

        <div ref="chatScroll" class="conversation-scroll" :class="{ empty: !messages.length }">
          <div v-if="!messages.length" class="start-panel">
            <div class="start-heading">
              <span class="start-mark"><el-icon><Search /></el-icon></span>
              <div>
                <h2>从当前项目资料开始查询</h2>
                <p>{{ currentProject && currentProject.name }}</p>
              </div>
            </div>

            <section class="project-lookup">
              <div class="start-section-title">查找其他项目资料库</div>
              <ProjectQuickSearch
                v-model="startProjectQuery"
                placeholder="例如：深圳市龙华区、学校名称"
                @select="selectSuggestedProject"
              />
            </section>

            <section class="start-section">
              <div class="start-section-title">常用查询</div>
              <div class="prompt-grid">
                <button v-for="prompt in quickPrompts" :key="prompt" type="button" @click="usePrompt(prompt)">
                  <span>{{ prompt }}</span>
                  <el-icon><ArrowRight /></el-icon>
                </button>
              </div>
            </section>

            <section v-if="recentProjects.length" class="start-section">
              <div class="start-section-title">最近访问的项目</div>
              <div class="recent-projects">
                <button v-for="project in recentProjects" :key="project.project_id" type="button"
                        @click="lockProject(project)">
                  <el-icon><Folder /></el-icon>
                  <span>{{ project.name }}</span>
                </button>
              </div>
            </section>
          </div>

          <div v-else class="message-list">
            <article v-for="(message, i) in messages" :key="i" class="message" :class="message.role">
              <div class="message-author">{{ message.role === 'user' ? '你' : 'ConstructionAgent' }}</div>
              <div class="message-content">
                <template v-if="message.role === 'ai'">
                  <span v-for="(segment, j) in renderAnswer(message.content)" :key="j">
                    <button v-if="segment.ref" class="citation" type="button"
                            @click="focusMessageEvidence(message, segment.ref)">E{{ segment.ref }}</button>
                    <span v-else>{{ segment.text }}</span>
                  </span>
                  <div v-if="message.fallback" class="fallback">未找到足够证据，建议人工核对项目资料。</div>
                </template>
                <template v-else>{{ message.content }}</template>
              </div>
            </article>
            <article v-if="thinking" class="message ai thinking-message">
              <div class="message-author">ConstructionAgent</div>
              <div class="message-content stage-line"><span class="stage-dot"></span>{{ stage || '正在处理' }}</div>
            </article>
          </div>
        </div>

        <form class="composer" @submit.prevent="ask">
          <el-input
            v-model="question"
            type="textarea"
            resize="none"
            :autosize="{ minRows: 2, maxRows: 5 }"
            placeholder="向当前项目知识库提问"
            @keydown.enter.exact.prevent="ask"
          />
          <div class="composer-footer">
            <button class="locked-context" type="button" @click="projectPickerOpen = true">
              <el-icon><Lock /></el-icon>
              <span>{{ currentProject && currentProject.name }}</span>
            </button>
            <el-button class="send-button" circle type="primary" native-type="submit"
                       :disabled="!question.trim() || thinking" title="发送">
              <el-icon><Position /></el-icon>
            </el-button>
          </div>
        </form>
      </main>

      <EvidencePanel
        v-if="evidenceVisible"
        class="desktop-evidence"
        :active-index="activeEv"
        :documents="documents"
        :evidences="evidences"
        :preview-url="previewUrl"
        @documents="documentsOpen = true"
        @open-document="openEvidenceDocument"
        @open-preview="openPreview"
        @upload="doUpload"
      />
    </div>

    <el-drawer v-model="navigationOpen" direction="ltr" size="280px" :with-header="false">
      <WorkspaceSidebar
        :current-project="currentProject"
        :projects="projects"
        :session-title="sessionTitle"
        @new-chat="newConversation(); navigationOpen = false"
        @select-project="lockProject"
        @switch-project="projectPickerOpen = true"
      />
    </el-drawer>

    <el-drawer v-model="evidenceDrawerOpen" title="检索依据" size="360px">
      <EvidencePanel
        :active-index="activeEv"
        :documents="documents"
        :evidences="evidences"
        :preview-url="previewUrl"
        @documents="documentsOpen = true"
        @open-document="openEvidenceDocument"
        @open-preview="openPreview"
        @upload="doUpload"
      />
    </el-drawer>

    <el-dialog v-model="projectPickerOpen" title="切换项目知识库" width="560px">
      <ProjectQuickSearch
        v-model="projectQuery"
        placeholder="输入项目名称或地区关键词"
        @select="selectSuggestedProject"
      />
      <div class="picker-list">
        <button v-for="project in matchedProjects" :key="project.project_id" type="button"
                :class="{ selected: currentProject && project.project_id === currentProject.project_id }"
                @click="lockProject(project)">
          <span class="picker-icon"><el-icon><Folder /></el-icon></span>
          <span class="picker-copy">
            <strong>{{ project.name }}</strong>
            <small>{{ project.description || '暂无项目描述' }}</small>
          </span>
          <el-tag v-if="currentProject && project.project_id === currentProject.project_id" size="small" type="success">已锁定</el-tag>
        </button>
      </div>
      <template #footer>
        <el-button @click="$router.push('/projects')">项目管理</el-button>
        <el-button @click="projectPickerOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="documentsOpen" title="项目资料库" size="min(520px, 94vw)">
      <div class="library-context">
        <span class="library-project-icon"><el-icon><Lock /></el-icon></span>
        <div>
          <strong>{{ currentProject && currentProject.name }}</strong>
          <span>已锁定当前项目 · {{ documents.length }} 份资料</span>
        </div>
      </div>
      <div class="library-toolbar">
        <el-input v-model="documentQuery" clearable placeholder="搜索文件名称">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="documentType" class="document-type-filter" placeholder="全部类型">
          <el-option label="全部类型" value="" />
          <el-option v-for="type in documentTypes" :key="type" :label="type" :value="type" />
        </el-select>
      </div>
      <el-empty v-if="!documents.length" description="暂无项目资料" :image-size="72" />
      <el-empty v-else-if="!filteredDocuments.length" description="没有匹配的文件" :image-size="64" />
      <button v-for="doc in filteredDocuments" :key="doc.document_id" class="document-row" type="button"
              @click="openProjectDocument(doc)">
        <span class="document-type">{{ fileType(doc.file_name) }}</span>
        <div class="document-main">
          <div class="document-name">{{ doc.file_name }}</div>
          <div class="document-meta">{{ doc.page_count }} 页 · {{ doc.chunk_count }} 个片段</div>
        </div>
        <el-tag size="small" :type="statusType(doc.parse_status)">{{ statusLabel(doc.parse_status) }}</el-tag>
      </button>
    </el-drawer>

    <el-drawer v-model="settingsOpen" title="工作台设置" size="380px">
      <div class="setting-row">
        <div><strong>显示 Evidence 栏</strong><span>桌面端右侧检索依据</span></div>
        <el-switch v-model="evidenceVisible" />
      </div>
      <div class="setting-row">
        <div><strong>紧凑模式</strong><span>缩小消息与面板间距</span></div>
        <el-switch v-model="compactMode" />
      </div>
      <div class="setting-block">
        <div class="setting-title"><strong>Evidence 数量</strong><span>{{ topK }}</span></div>
        <el-slider v-model="topK" :min="2" :max="20" :step="1" show-stops />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, Folder, Lock, Position, Search } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import EvidencePanel from '../components/EvidencePanel.vue'
import ProjectQuickSearch from '../components/ProjectQuickSearch.vue'
import WorkspaceSidebar from '../components/WorkspaceSidebar.vue'
import WorkspaceTopbar from '../components/WorkspaceTopbar.vue'
import { fetchProtectedBlobUrl, request, streamQuery, uploadDocument } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspace'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const projectId = computed(() => Number(route.params.id))
const projects = ref([])
const currentProject = ref(null)
const documents = ref([])
const messages = ref([])
const evidences = ref([])
const question = ref('')
const thinking = ref(false)
const stage = ref('')
const activeEv = ref(-1)
const previewUrl = ref('')
const projectQuery = ref('')
const startProjectQuery = ref('')
const documentQuery = ref('')
const documentType = ref('')
const projectPickerOpen = ref(false)
const documentsOpen = ref(false)
const settingsOpen = ref(false)
const navigationOpen = ref(false)
const evidenceDrawerOpen = ref(false)
const chatScroll = ref(null)
let evidenceLoadVersion = 0
let previewBlobUrl = ''
let previewLoadVersion = 0
let documentPollTimer = 0

const quickPrompts = [
  '这个项目采用什么接地系统？',
  '项目中的配电箱安装有什么要求？',
  '消防应急照明采用什么方式？',
  '列出项目资料中的关键技术参数。'
]

const evidenceVisible = computed({
  get: () => workspace.evidenceVisible,
  set: value => workspace.setEvidenceVisible(value)
})
const compactMode = computed({
  get: () => workspace.compactMode,
  set: value => workspace.setCompactMode(value)
})
const topK = computed({
  get: () => workspace.topK,
  set: value => workspace.setTopK(value)
})
const readyDocumentCount = computed(() => documents.value.filter(doc => doc.parse_status === 'READY').length)
const sessionTitle = computed(() => {
  const first = messages.value.find(message => message.role === 'user')
  return first ? first.content : ''
})
const recentProjects = computed(() => workspace.recentProjectIds
  .map(id => projects.value.find(project => project.project_id === id))
  .filter(project => project && project.project_id !== projectId.value)
  .slice(0, 4))
const matchedProjects = computed(() => {
  const keyword = projectQuery.value.trim().toLowerCase()
  return projects.value.filter(project => !keyword || project.name.toLowerCase().includes(keyword))
})
const documentTypes = computed(() => [...new Set(documents.value.map(doc => fileType(doc.file_name)))].sort())
const filteredDocuments = computed(() => {
  const keyword = documentQuery.value.trim().toLowerCase()
  return documents.value.filter(doc =>
    (!keyword || doc.file_name.toLowerCase().includes(keyword)) &&
    (!documentType.value || fileType(doc.file_name) === documentType.value))
})

function renderAnswer(text) {
  const segments = []
  const pattern = /\[E(\d+)\]/g
  let last = 0
  let match
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) segments.push({ text: text.slice(last, match.index) })
    segments.push({ ref: Number(match[1]) })
    last = match.index + match[0].length
  }
  if (last < text.length) segments.push({ text: text.slice(last) })
  return segments
}

function statusLabel(status) {
  return { PENDING: '等待处理', PARSING: '解析中', READY: '可检索', FAILED: '解析失败' }[status] || status
}

function statusType(status) {
  return { PENDING: 'info', PARSING: 'warning', READY: 'success', FAILED: 'danger' }[status] || 'info'
}

function fileType(fileName) {
  const extension = fileName.split('.').pop()
  return extension ? extension.slice(0, 4).toUpperCase() : 'FILE'
}

function scheduleDocumentPoll() {
  window.clearTimeout(documentPollTimer)
  if (documents.value.some(doc => ['PENDING', 'PARSING'].includes(doc.parse_status))) {
    documentPollTimer = window.setTimeout(loadDocuments, 2000)
  }
}

async function loadDocuments() {
  try {
    const data = await request('GET', '/projects/' + projectId.value + '/documents')
    documents.value = data.items
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    scheduleDocumentPoll()
  }
}

async function loadWorkspace() {
  const [projectList, projectDetail] = await Promise.all([
    request('GET', '/projects'),
    request('GET', '/projects/' + projectId.value)
  ])
  projects.value = projectList.items
  currentProject.value = projectDetail
  workspace.rememberProject(projectId.value)
  await loadDocuments()
}

function revokeEvidenceUrls() {
  for (const evidence of evidences.value) {
    if (evidence.thumbnail_blob_url) URL.revokeObjectURL(evidence.thumbnail_blob_url)
  }
}

function clearPreview() {
  ++previewLoadVersion
  if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl)
  previewBlobUrl = ''
  previewUrl.value = ''
}

async function setEvidences(items) {
  const version = ++evidenceLoadVersion
  revokeEvidenceUrls()
  evidences.value = items.map(evidence => ({ ...evidence, thumbnail_blob_url: '' }))
  await Promise.all(evidences.value.map(async evidence => {
    if (!evidence.thumbnail_url) return
    try {
      const blobUrl = await fetchProtectedBlobUrl(evidence.thumbnail_url)
      if (version !== evidenceLoadVersion) URL.revokeObjectURL(blobUrl)
      else evidence.thumbnail_blob_url = blobUrl
    } catch (e) {
      if (version === evidenceLoadVersion) evidence.preview_error = e.message
    }
  }))
}

async function focusEvidence(index) {
  activeEv.value = index - 1
  const evidence = evidences.value[index - 1]
  clearPreview()
  if (!evidence || !evidence.thumbnail_url) return
  const version = previewLoadVersion
  try {
    const blobUrl = await fetchProtectedBlobUrl(
      '/projects/' + projectId.value + '/documents/' + evidence.file_id + '/preview')
    if (version !== previewLoadVersion) {
      URL.revokeObjectURL(blobUrl)
      return
    }
    previewBlobUrl = blobUrl
    previewUrl.value = blobUrl + '#page=' + evidence.page
    workspace.setEvidenceVisible(true)
    if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
  } catch (e) {
    ElMessage.error('无法打开证据文件：' + e.message)
  }
}

async function focusMessageEvidence(message, index) {
  if (message.evidences && message.evidences.length) await setEvidences(message.evidences)
  await focusEvidence(index)
}

async function openEvidenceDocument(index) {
  activeEv.value = index - 1
  const evidence = evidences.value[index - 1]
  if (!evidence || !evidence.thumbnail_url) return
  const viewer = window.open('about:blank', '_blank')
  if (viewer) viewer.opener = null
  try {
    const blobUrl = await fetchProtectedBlobUrl(
      '/projects/' + projectId.value + '/documents/' + evidence.file_id + '/preview')
    const target = blobUrl + '#page=' + evidence.page
    if (viewer) {
      viewer.location.replace(target)
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
    } else {
      clearPreview()
      previewBlobUrl = blobUrl
      previewUrl.value = target
      ElMessage.warning('浏览器拦截了新窗口，已在 Evidence 栏打开')
    }
  } catch (e) {
    if (viewer) viewer.close()
    ElMessage.error('无法打开完整文件：' + e.message)
  }
}

function openPreview() {
  if (previewUrl.value) window.open(previewUrl.value, '_blank', 'noopener,noreferrer')
}

function openEvidencePanel() {
  if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
  else workspace.setEvidenceVisible(true)
}

function newConversation() {
  messages.value = []
  question.value = ''
  thinking.value = false
  ++evidenceLoadVersion
  revokeEvidenceUrls()
  evidences.value = []
  activeEv.value = -1
  clearPreview()
}

function usePrompt(prompt) {
  question.value = prompt
  nextTick(() => ask())
}

async function ask() {
  const query = question.value.trim()
  if (!query || thinking.value) return
  messages.value.push({ role: 'user', content: query })
  question.value = ''
  thinking.value = true
  stage.value = '正在分析问题'
  ++evidenceLoadVersion
  revokeEvidenceUrls()
  evidences.value = []
  activeEv.value = -1
  clearPreview()
  const answerMessage = { role: 'ai', content: '', fallback: false, evidences: [] }
  messages.value.push(answerMessage)
  await scrollToBottom()
  try {
    await streamQuery(projectId.value, query, (event, data) => {
      if (event === 'stage') stage.value = data.message
      if (event === 'evidence') {
        answerMessage.evidences = data.evidences
        setEvidences(data.evidences)
      }
      if (event === 'token') answerMessage.content += data.delta
      if (event === 'done') {
        if (data.answer) answerMessage.content = data.answer
        if (data.evidences) answerMessage.evidences = data.evidences
        if (data.evidences && !evidences.value.length) setEvidences(data.evidences)
        if (!data.evidences || !data.evidences.length) answerMessage.fallback = true
      }
      if (event === 'error') answerMessage.content = '请求失败：' + data.message
      scrollToBottom()
    }, topK.value)
  } catch (e) {
    answerMessage.content = '请求失败：' + e.message
  } finally {
    thinking.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight
}

async function doUpload(options) {
  try {
    const data = await uploadDocument(projectId.value, options.file)
    options.onSuccess(data)
    documentsOpen.value = true
    await loadDocuments()
    ElMessage.success('已上传：' + data.file_name)
  } catch (e) {
    options.onError(e)
    ElMessage.error('上传失败：' + e.message)
  }
}

async function openProjectDocument(doc) {
  const viewer = window.open('about:blank', '_blank')
  if (viewer) viewer.opener = null
  try {
    let blobUrl
    try {
      blobUrl = await fetchProtectedBlobUrl(
        '/projects/' + projectId.value + '/documents/' + doc.document_id + '/preview')
    } catch (previewError) {
      blobUrl = await fetchProtectedBlobUrl(
        '/projects/' + projectId.value + '/documents/' + doc.document_id + '/file')
    }
    if (!viewer) {
      URL.revokeObjectURL(blobUrl)
      ElMessage.warning('浏览器拦截了文件窗口，请允许本站打开新窗口')
      return
    }
    viewer.location.replace(blobUrl)
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
  } catch (e) {
    if (viewer) viewer.close()
    ElMessage.error('无法打开项目文件：' + e.message)
  }
}

function selectSuggestedProject(project) {
  projectQuery.value = ''
  startProjectQuery.value = ''
  lockProject(project, true)
}

function lockProject(project, showLibrary = false) {
  projectPickerOpen.value = false
  navigationOpen.value = false
  if (project.project_id !== projectId.value) {
    router.push({ path: '/projects/' + project.project_id,
                  query: showLibrary ? { library: '1' } : {} })
  } else if (showLibrary) {
    documentsOpen.value = true
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

watch(projectId, async () => {
  window.clearTimeout(documentPollTimer)
  documentQuery.value = ''
  documentType.value = ''
  newConversation()
  try {
    await loadWorkspace()
  } catch (e) {
    ElMessage.error(e.message)
  }
}, { immediate: true })

watch(() => route.query.library, value => {
  if (value === '1') documentsOpen.value = true
}, { immediate: true })

onBeforeUnmount(() => {
  window.clearTimeout(documentPollTimer)
  ++evidenceLoadVersion
  revokeEvidenceUrls()
  clearPreview()
})
</script>

<style scoped>
.workspace { --topbar-height: 56px; height: 100vh; background: #eef1f5; color: #24303c; overflow: hidden; }
.workspace-body { height: calc(100vh - var(--topbar-height)); display: grid; grid-template-columns: 252px minmax(520px, 1fr) 340px; }
.workspace-body.without-evidence { grid-template-columns: 252px minmax(520px, 1fr); }
.conversation-panel { min-width: 0; display: grid; grid-template-rows: 64px minmax(0, 1fr) auto; background: #fff; }
.conversation-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 24px; border-bottom: 1px solid #e2e6ea; }
.conversation-title { min-width: 0; }
.agent-label { color: #1f5fbf; font-size: 11px; font-weight: 700; }
.conversation-title h1 { margin: 3px 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 16px; letter-spacing: 0; }
.knowledge-status { display: flex; align-items: center; gap: 6px; color: #617080; font-size: 11px; white-space: nowrap; }
.knowledge-status :deep(.el-icon) { color: #25855a; }
.knowledge-status strong { color: #2d3748; }
.conversation-scroll { min-height: 0; overflow-y: auto; background: #f8fafc; }
.conversation-scroll.empty { display: grid; place-items: center; }
.start-panel { width: min(720px, calc(100% - 40px)); padding: 28px 0 40px; }
.start-heading { display: flex; align-items: center; gap: 14px; margin-bottom: 30px; }
.start-mark { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 6px; background: #e6eef9; color: #1f5fbf; font-size: 20px; }
.start-heading h2 { margin: 0; font-size: 22px; letter-spacing: 0; }
.start-heading p { margin: 6px 0 0; color: #708090; font-size: 13px; }
.start-section { margin-top: 24px; }
.start-section-title { margin-bottom: 10px; color: #687586; font-size: 12px; font-weight: 600; }
.project-lookup { margin-bottom: 24px; }
.project-lookup :deep(.el-input__wrapper) { min-height: 42px; }
.prompt-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); border-top: 1px solid #dfe4ea; border-left: 1px solid #dfe4ea; }
.prompt-grid button { min-height: 52px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; border: 0; border-right: 1px solid #dfe4ea; border-bottom: 1px solid #dfe4ea; background: #fff; color: #344054; cursor: pointer; text-align: left; font-size: 13px; }
.prompt-grid button:hover { background: #f2f6fb; color: #174ea6; }
.recent-projects { display: flex; flex-wrap: wrap; gap: 8px; }
.recent-projects button { max-width: 240px; height: 34px; display: flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid #d7dde5; border-radius: 5px; background: #fff; color: #52606d; cursor: pointer; }
.recent-projects button span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.message-list { width: min(860px, calc(100% - 44px)); margin: 0 auto; padding: 28px 0 80px; }
.message { display: grid; grid-template-columns: 108px minmax(0, 1fr); gap: 14px; padding: 18px 0; border-bottom: 1px solid #e4e8ed; }
.message-author { color: #667085; font-size: 12px; font-weight: 600; }
.message-content { min-width: 0; color: #263445; font-size: 14px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.message.user .message-content { color: #17202a; font-weight: 500; }
.citation { display: inline-grid; place-items: center; min-width: 25px; height: 20px; margin: 0 2px; padding: 0 5px; border: 1px solid #8eb0df; border-radius: 4px; background: #edf4ff; color: #174ea6; cursor: pointer; font-size: 11px; vertical-align: 1px; }
.citation:hover { background: #dbe9fb; }
.fallback { margin-top: 10px; padding-left: 9px; border-left: 3px solid #d69e2e; color: #8a5a12; }
.stage-line { color: #667085; }
.stage-dot { width: 7px; height: 7px; display: inline-block; margin-right: 8px; border-radius: 50%; background: #2f6fc7; animation: pulse 1.2s infinite; }
.composer { margin: 0 20px 16px; padding: 10px 12px 8px; border: 1px solid #cfd7e2; border-radius: 7px; background: #fff; box-shadow: 0 4px 16px rgba(31, 45, 61, .08); }
.composer :deep(.el-textarea__inner) { min-height: 48px !important; padding: 4px; border: 0; box-shadow: none; font-size: 14px; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 5px; }
.locked-context { min-width: 0; display: flex; align-items: center; gap: 6px; padding: 0; border: 0; background: transparent; color: #687586; cursor: pointer; font-size: 11px; }
.locked-context span { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.send-button { flex: 0 0 auto; }
.picker-list { max-height: 420px; margin-top: 12px; overflow-y: auto; border-top: 1px solid #e2e6ea; }
.picker-list > button { width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px 8px; border: 0; border-bottom: 1px solid #e7eaee; background: #fff; color: #344054; cursor: pointer; text-align: left; }
.picker-list > button:hover, .picker-list > button.selected { background: #f2f6fb; }
.picker-icon { width: 32px; height: 32px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 5px; background: #edf1f5; color: #52606d; }
.picker-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 4px; }
.picker-copy strong, .picker-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.picker-copy small { color: #7b8794; }
.library-context { display: flex; align-items: center; gap: 10px; padding: 12px; border: 1px solid #d8e1ed; border-radius: 6px; background: #f7f9fc; }
.library-project-icon { width: 34px; height: 34px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 5px; background: #e8f0fb; color: #1f5fbf; }
.library-context > div { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.library-context strong, .library-context span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.library-context strong { font-size: 13px; }
.library-context span { color: #7a8594; font-size: 11px; }
.library-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) 112px; gap: 8px; margin: 14px 0 6px; }
.document-type-filter { width: 112px; }
.document-row { width: 100%; display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 12px 4px; border: 0; border-bottom: 1px solid #e5e8ec; background: transparent; color: #263445; cursor: pointer; text-align: left; }
.document-row:hover { background: #f5f8fc; }
.document-type { width: 42px; height: 34px; display: grid; place-items: center; border-radius: 4px; background: #edf1f5; color: #52606d; font-size: 10px; font-weight: 700; }
.document-main { min-width: 0; }
.document-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.document-meta { margin-top: 4px; color: #8a94a3; font-size: 11px; }
.setting-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 0; border-bottom: 1px solid #e5e8ec; }
.setting-row > div { display: flex; flex-direction: column; gap: 5px; }
.setting-row strong, .setting-title strong { font-size: 13px; }
.setting-row span, .setting-title span { color: #7a8594; font-size: 11px; }
.setting-block { padding: 18px 0; }
.setting-title { display: flex; justify-content: space-between; margin-bottom: 14px; }
.compact .message { padding: 11px 0; }
.compact .message-list { padding-top: 16px; }
.compact .conversation-header { height: 52px; }
@keyframes pulse { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
@media (max-width: 1280px) {
  .workspace-body { grid-template-columns: 224px minmax(480px, 1fr) 300px; }
  .workspace-body.without-evidence { grid-template-columns: 224px minmax(480px, 1fr); }
}
@media (max-width: 1040px) {
  .workspace-body, .workspace-body.without-evidence { grid-template-columns: 224px minmax(0, 1fr); }
  .desktop-evidence { display: none; }
}
@media (max-width: 760px) {
  .workspace-body, .workspace-body.without-evidence { grid-template-columns: minmax(0, 1fr); }
  .desktop-navigation { display: none; }
  .conversation-header { padding: 0 14px; }
  .knowledge-status span { display: none; }
  .start-panel { width: calc(100% - 28px); }
  .prompt-grid { grid-template-columns: 1fr; }
  .message-list { width: calc(100% - 28px); }
  .message { grid-template-columns: 1fr; gap: 5px; }
  .composer { margin: 0 10px 10px; }
}
</style>
