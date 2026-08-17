<template>
  <div class="workspace" :class="{ compact: compactMode }">
    <WorkspaceTopbar
      :user="auth.user"
      :project="currentProject"
      :evidence-count="evidences.length"
      @logout="logout"
      @open-evidence="openEvidencePanel"
      @open-navigation="navigationOpen = true"
      @projects="projectPickerOpen = true"
      @settings="settingsOpen = true"
      @switch-project="projectPickerOpen = true"
    />

    <div class="workspace-body">
      <WorkspaceSidebar
        class="desktop-navigation"
        :active-agent="activeAgent"
        :current-project="currentProject"
        :projects="projects"
        :session-title="sessionTitle"
        @new-chat="newConversation"
        @select-agent="selectAgent"
        @select-project="lockProject"
        @switch-project="projectPickerOpen = true"
      />

      <main class="conversation-panel">
        <header class="conversation-header">
          <div class="conversation-title">
            <span class="agent-label">{{ activeAgentLabel }}</span>
            <h1>{{ conversationHeading }}</h1>
          </div>
          <div class="knowledge-status">
            <el-icon><Lock /></el-icon>
            <span>{{ activeAgent === 'standard' ? '规范库已连接' : '知识库已锁定' }}</span>
            <strong>{{ readyDocumentCount }}/{{ libraryDocuments.length }}</strong>
          </div>
        </header>

        <div ref="chatScroll" class="conversation-scroll">
          <div class="message-list">
            <article v-for="(message, i) in messages" :key="message.message_id || i" class="message" :class="message.role">
              <div class="message-author">{{ message.role === 'user' ? '你' : 'ConstructionAgent' }}</div>
              <div class="message-content">
                <template v-if="message.role === 'ai'">
                  <span v-for="(segment, j) in renderAnswer(message.content)" :key="j">
                    <button v-if="segment.ref" class="citation" type="button"
                            @click="focusMessageEvidence(message, segment.ref)">E{{ segment.ref }}</button>
                    <span v-else>{{ segment.text }}</span>
                  </span>
                  <div v-if="message.actions" class="assistant-actions">
                    <button v-for="action in message.actions" :key="action.id" type="button"
                            :disabled="action.disabled" @click="handleAssistantAction(action)">
                      <el-icon><component :is="action.icon" /></el-icon>
                      <span>{{ action.label }}</span>
                      <small v-if="action.disabled">即将开放</small>
                    </button>
                  </div>
                  <div v-if="message.projects" class="project-suggestions">
                    <button v-for="project in message.projects" :key="project.project_id" type="button"
                            @click="chooseProjectFromChat(project)">
                      <span class="suggestion-folder"><el-icon><Folder /></el-icon></span>
                      <span>
                        <strong>{{ project.name }}</strong>
                        <small>{{ project.description || '可访问项目' }} · {{ project.document_count || 0 }} 份资料</small>
                      </span>
                      <el-icon><ArrowRight /></el-icon>
                    </button>
                  </div>
                  <div v-if="message.fallback" class="fallback">未找到足够证据，建议人工核对项目资料。</div>
                  <div v-if="message.planDownloads" class="plan-downloads">
                    <el-button type="primary" plain @click="openPlanDocument(message.planDownloads.docx)">
                      <el-icon><Download /></el-icon>下载 DOCX
                    </el-button>
                    <el-button @click="openPlanDocument(message.planDownloads.pdf)">
                      <el-icon><Download /></el-icon>查看 PDF
                    </el-button>
                  </div>
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
            :placeholder="composerPlaceholder"
            @keydown.enter.exact.prevent="ask"
          />
          <div class="composer-footer">
            <button class="locked-context" type="button" @click="projectPickerOpen = true">
              <el-icon><Lock /></el-icon>
              <span>{{ activeAgent === 'standard' ? '企业规范知识库' : currentProject && currentProject.name }}</span>
            </button>
            <el-button class="send-button" circle type="primary" native-type="submit"
                       :disabled="!question.trim() || thinking" title="发送">
              <el-icon><Position /></el-icon>
            </el-button>
          </div>
        </form>
      </main>

      <EvidencePanel
        class="desktop-evidence"
        v-model:mode="contextMode"
        :active-document-id="activeDocumentId"
        :active-index="activeEv"
        :can-upload="activeAgent === 'project' || auth.user && auth.user.role === 'admin'"
        :documents="libraryDocuments"
        :evidences="evidences"
        :folders="activeAgent === 'project' ? folders : []"
        :library-label="activeAgent === 'standard' ? '规范文件' : '项目文件'"
        :preview-label="previewLabel"
        :preview-url="previewUrl"
        :project="libraryContext"
        :selected-folder-id="selectedFolderId"
        :show-folders="activeAgent === 'project'"
        :upload-title="activeAgent === 'standard' ? '上传规范文件' : '上传项目资料'"
        :workspace-title="activeAgent === 'standard' ? '规范工作区' : '项目工作区'"
        @create-folder="createFolder"
        @delete-folder="deleteFolder"
        @focus-evidence="focusEvidence"
        @open-preview="openPreview"
        @open-project-document="previewProjectDocument"
        @rename-folder="renameFolder"
        @select-folder="selectedFolderId = $event"
        @upload="doUpload"
      />
    </div>

    <el-drawer v-model="navigationOpen" direction="ltr" size="280px" :with-header="false">
      <WorkspaceSidebar
        :active-agent="activeAgent"
        :current-project="currentProject"
        :projects="projects"
        :session-title="sessionTitle"
        @new-chat="newConversation(); navigationOpen = false"
        @select-agent="selectAgent"
        @select-project="lockProject"
        @switch-project="projectPickerOpen = true"
      />
    </el-drawer>

    <el-drawer v-model="evidenceDrawerOpen" title="项目工作区" size="min(420px, 94vw)">
      <EvidencePanel
        v-model:mode="contextMode"
        :active-document-id="activeDocumentId"
        :active-index="activeEv"
        :can-upload="activeAgent === 'project' || auth.user && auth.user.role === 'admin'"
        :documents="libraryDocuments"
        :evidences="evidences"
        :folders="activeAgent === 'project' ? folders : []"
        :library-label="activeAgent === 'standard' ? '规范文件' : '项目文件'"
        :preview-label="previewLabel"
        :preview-url="previewUrl"
        :project="libraryContext"
        :selected-folder-id="selectedFolderId"
        :show-folders="activeAgent === 'project'"
        :upload-title="activeAgent === 'standard' ? '上传规范文件' : '上传项目资料'"
        :workspace-title="activeAgent === 'standard' ? '规范工作区' : '项目工作区'"
        @create-folder="createFolder"
        @delete-folder="deleteFolder"
        @focus-evidence="focusEvidence"
        @open-preview="openPreview"
        @open-project-document="previewProjectDocument"
        @rename-folder="renameFolder"
        @select-folder="selectedFolderId = $event"
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
        <el-button type="primary" plain @click="projectCreateOpen = true">
          <el-icon><Plus /></el-icon>
          新建项目
        </el-button>
        <el-button @click="projectPickerOpen = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="projectCreateOpen" title="新建项目" width="480px">
      <el-form label-position="top" @submit.prevent="createProject">
        <el-form-item label="项目名称" required>
          <el-input v-model="projectForm.name" maxlength="128" />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="projectForm.description" type="textarea" :rows="3" maxlength="512" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectCreateOpen = false">取消</el-button>
        <el-button type="primary" :loading="projectCreating" :disabled="!projectForm.name.trim()" @click="createProject">
          创建并切换
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="settingsOpen" title="工作台设置" size="380px">
      <div class="setting-row">
        <div><strong>紧凑模式</strong><span>缩小消息与面板间距</span></div>
        <el-switch v-model="compactMode" />
      </div>
      <div class="setting-block">
        <div class="setting-title"><strong>Evidence 数量</strong><span>{{ topK }}</span></div>
        <el-slider v-model="topK" :min="2" :max="20" :step="1" show-stops />
      </div>
    </el-drawer>

    <el-dialog v-model="standardUploadOpen" title="录入规范文件" width="620px">
      <el-form label-position="top" :model="standardForm">
        <div class="standard-form-grid">
          <el-form-item class="span-two" label="规范名称" required>
            <el-input v-model="standardForm.standard_name" placeholder="例如：建筑设计防火规范" />
          </el-form-item>
          <el-form-item label="规范编号">
            <el-input v-model="standardForm.standard_code" placeholder="例如：GB 50016-2014" />
          </el-form-item>
          <el-form-item label="版本">
            <el-input v-model="standardForm.version" placeholder="例如：2018年版" />
          </el-form-item>
          <el-form-item label="适用地区">
            <el-input v-model="standardForm.region" placeholder="全国 / 广东 / 深圳" />
          </el-form-item>
          <el-form-item label="专业">
            <el-select v-model="standardForm.discipline" clearable placeholder="选择专业">
              <el-option v-for="item in standardDisciplines" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="规范类型">
            <el-select v-model="standardForm.standard_type">
              <el-option v-for="item in standardTypes" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="有效状态" required>
            <el-select v-model="standardForm.status">
              <el-option label="现行" value="active" />
              <el-option label="状态未知" value="unknown" />
              <el-option label="废止" value="repealed" />
              <el-option label="被替代" value="replaced" />
              <el-option label="即将实施" value="upcoming" />
            </el-select>
          </el-form-item>
          <el-form-item label="发布日期">
            <el-date-picker v-model="standardForm.publish_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="实施日期">
            <el-date-picker v-model="standardForm.effective_date" type="date" value-format="YYYY-MM-DD" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="cancelStandardUpload">取消</el-button>
        <el-button type="primary" :loading="standardUploading" @click="submitStandardUpload">上传并解析</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="planDecisionOpen" :title="planDecisionTitle" width="min(720px, 94vw)"
               :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
      <template v-if="planTask && ['TEMPLATE_SELECTION', 'GENERIC_TEMPLATE_PERMISSION'].includes(planTask.human_reason)">
        <p class="decision-message">{{ planTask.human_payload.message }}</p>
        <el-radio-group v-if="planTask.human_payload.templates && planTask.human_payload.templates.length"
                        v-model="selectedTemplateId" class="template-options">
          <el-radio v-for="template in planTask.human_payload.templates" :key="template.document_id"
                    :value="template.document_id" border>
            {{ template.name }}{{ template.version ? ' · ' + template.version : '' }}
          </el-radio>
          <el-radio value="__generic__" border>不使用模板，生成通用结构</el-radio>
        </el-radio-group>
      </template>

      <template v-else-if="planTask && planTask.human_reason === 'OUTLINE_CONFIRMATION'">
        <p class="decision-message">{{ planTask.human_payload.message }}</p>
        <div class="outline-editor">
          <div v-for="(item, index) in planOutline" :key="index" class="outline-row">
            <span>{{ index + 1 }}</span>
            <el-input v-model="planOutline[index]" maxlength="128" />
            <el-button circle text title="删除章节" @click="planOutline.splice(index, 1)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <el-button text type="primary" :disabled="planOutline.length >= 15"
                     @click="planOutline.push('')"><el-icon><Plus /></el-icon>增加章节</el-button>
        </div>
      </template>

      <template v-else-if="planTask && planTask.human_reason === 'FINAL_REVIEW'">
        <el-alert :type="planTask.high_risk ? 'error' : 'warning'" :closable="false"
                  :title="planTask.human_payload.message" show-icon />
        <div v-if="planTask.warnings.length" class="review-warnings">
          <strong>人工审核项</strong>
          <ul><li v-for="item in planTask.warnings" :key="item">{{ item }}</li></ul>
        </div>
        <el-input v-model="planComment" type="textarea" :rows="3" maxlength="1000"
                  placeholder="退回修改时填写具体意见" />
        <details class="plan-preview">
          <summary>查看方案草案</summary>
          <pre>{{ planTask.final_content }}</pre>
        </details>
      </template>

      <template #footer>
        <el-button :loading="planDecisionLoading" @click="submitPlanDecision('cancel')">取消任务</el-button>
        <el-button v-if="planTask && planTask.human_reason === 'FINAL_REVIEW'"
                   :loading="planDecisionLoading" @click="submitPlanDecision('return_modify')">退回修改</el-button>
        <el-button type="primary" :loading="planDecisionLoading" :disabled="!canSubmitPlanDecision"
                   @click="submitPlanDecision(primaryPlanDecision)">{{ primaryPlanDecisionLabel }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, Delete, Download, EditPen, Folder, Lock, Plus, Position, Reading, Search } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import EvidencePanel from '../components/EvidencePanel.vue'
import ProjectQuickSearch from '../components/ProjectQuickSearch.vue'
import WorkspaceSidebar from '../components/WorkspaceSidebar.vue'
import WorkspaceTopbar from '../components/WorkspaceTopbar.vue'
import { fetchProtectedBlobUrl, request, streamQuery, streamStandardQuery,
  uploadDocument, uploadStandardDocument } from '../api/client'
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
const folders = ref([])
const selectedFolderId = ref('')
const activeAgent = ref('project')
const standards = ref([])
const messages = ref([createWelcomeMessage()])
const evidences = ref([])
const conversationId = ref('')
const question = ref('')
const thinking = ref(false)
const stage = ref('')
const activeEv = ref(-1)
const previewUrl = ref('')
const previewLabel = ref('')
const activeDocumentId = ref('')
const contextMode = ref('files')
const projectQuery = ref('')
const projectPickerOpen = ref(false)
const projectCreateOpen = ref(false)
const projectCreating = ref(false)
const projectForm = reactive({ name: '', description: '' })
const settingsOpen = ref(false)
const navigationOpen = ref(false)
const evidenceDrawerOpen = ref(false)
const standardUploadOpen = ref(false)
const standardUploading = ref(false)
const standardUploadOptions = ref(null)
const standardForm = reactive(createStandardForm())
const chatScroll = ref(null)
let evidenceLoadVersion = 0
let previewBlobUrl = ''
let previewLoadVersion = 0
let documentPollTimer = 0
let planPollTimer = 0
let planAnswerMessage = null
const standardDisciplines = ['建筑', '结构', '给排水', '电气', '暖通', '消防', '市政', '园林']
const standardTypes = ['国家标准', '行业标准', '地方标准', '标准图集', '企业规范', '项目指定规范']

const compactMode = computed({
  get: () => workspace.compactMode,
  set: value => workspace.setCompactMode(value)
})
const topK = computed({
  get: () => workspace.topK,
  set: value => workspace.setTopK(value)
})
const libraryDocuments = computed(() => activeAgent.value === 'standard'
  ? standards.value : documents.value)
const readyDocumentCount = computed(() => libraryDocuments.value.filter(
  doc => doc.parse_status === 'READY').length)
const activeAgentLabel = computed(() => activeAgent.value === 'standard'
  ? '工程规范查询' : activeAgent.value === 'plan' ? '施工方案编制' : '项目资料检索')
const conversationHeading = computed(() => activeAgent.value === 'standard'
  ? '工程规范查询' : activeAgent.value === 'plan' ? '施工方案任务' :
    (currentProject.value ? currentProject.value.name : '项目工作台'))
const composerPlaceholder = computed(() => activeAgent.value === 'standard'
  ? '查询规范编号、条款、地区适用性或有效状态'
  : activeAgent.value === 'plan' ? '例如：编制地下室防水施工方案' : '向当前项目知识库提问')
const libraryContext = computed(() => activeAgent.value === 'standard'
  ? { name: '企业规范知识库' } : currentProject.value)
const sessionTitle = computed(() => {
  const first = messages.value.find(message => message.role === 'user')
  return first ? first.content : ''
})
const matchedProjects = computed(() => {
  const keyword = projectQuery.value.trim().toLowerCase()
  return projects.value.filter(project => !keyword || project.name.toLowerCase().includes(keyword))
})
const planTask = ref(null)
const planDecisionOpen = ref(false)
const planDecisionLoading = ref(false)
const selectedTemplateId = ref('')
const planOutline = ref([])
const planComment = ref('')
const planDecisionTitle = computed(() => {
  if (!planTask.value) return '方案人工确认'
  if (planTask.value.human_reason === 'OUTLINE_CONFIRMATION') return '确认方案目录'
  if (planTask.value.human_reason === 'FINAL_REVIEW') return '施工方案最终审核'
  return '确认企业模板'
})
const primaryPlanDecision = computed(() => {
  if (!planTask.value) return ''
  if (planTask.value.human_reason === 'OUTLINE_CONFIRMATION') return 'confirm'
  if (planTask.value.human_reason === 'FINAL_REVIEW') return 'approve'
  return selectedTemplateId.value && selectedTemplateId.value !== '__generic__'
    ? 'select_template' : 'use_generic'
})
const primaryPlanDecisionLabel = computed(() => {
  if (primaryPlanDecision.value === 'confirm') return '确认目录并生成'
  if (primaryPlanDecision.value === 'approve') return '审核通过并生成文档'
  return primaryPlanDecision.value === 'select_template' ? '使用所选模板' : '使用通用结构'
})
const canSubmitPlanDecision = computed(() => {
  if (!planTask.value) return false
  if (planTask.value.human_reason === 'OUTLINE_CONFIRMATION') {
    return planOutline.value.length > 0 && planOutline.value.every(item => item.trim())
  }
  return planTask.value.human_reason !== 'TEMPLATE_SELECTION' || Boolean(selectedTemplateId.value)
})

function createWelcomeMessage() {
  if (activeAgent.value === 'standard') {
    return {
      role: 'ai',
      content: '已进入工程规范查询。请告诉我规范编号、工程地区、专业或需要核对的具体做法。'
    }
  }
  if (activeAgent.value === 'plan') {
    return {
      role: 'ai',
      content: '已进入施工方案编制。方案将依次经过企业模板确认、目录确认、Evidence 检索、自动检查和最终人工审核。'
    }
  }
  return {
    role: 'ai',
    content: '你好，我是智能 AI 建筑辅助功能。\n我可以为您查找项目资料、查询工程规范、编制施工方案。请告诉我您想处理的项目或问题。',
    actions: [
      { id: 'project', label: '查找项目资料', icon: Search },
      { id: 'standard', label: '查询工程规范', icon: Reading },
      { id: 'plan', label: '编制施工方案', icon: EditPen }
    ]
  }
}

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

function scheduleDocumentPoll() {
  window.clearTimeout(documentPollTimer)
  if ([...documents.value, ...standards.value].some(
      doc => ['PENDING', 'PARSING'].includes(doc.parse_status))) {
    documentPollTimer = window.setTimeout(async () => {
      await Promise.all([loadDocuments(), loadStandards()])
    }, 2000)
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

async function loadStandards() {
  try {
    const data = await request('GET', '/standards/documents')
    standards.value = data.items.map(item => ({
      ...item, source_type: 'STANDARD_DOCUMENT'
    }))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    scheduleDocumentPoll()
  }
}

async function loadFolders() {
  try {
    const data = await request('GET', '/projects/' + projectId.value + '/folders')
    folders.value = data.items
    if (selectedFolderId.value &&
        !folders.value.some(folder => folder.folder_id === selectedFolderId.value)) {
      selectedFolderId.value = ''
    }
  } catch (e) {
    ElMessage.error(e.message)
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
  await Promise.all([loadDocuments(), loadFolders(), loadStandards()])
  await loadConversation()
}

async function loadConversation() {
  if (activeAgent.value === 'plan') {
    await loadLatestPlanTask()
    return
  }
  const storedId = workspace.getConversation(projectId.value, activeAgent.value)
  if (!storedId) return
  try {
    const data = await request(
      'GET', '/projects/' + projectId.value + '/conversations/' + storedId +
      '?agent_type=' + encodeURIComponent(activeAgent.value))
    conversationId.value = data.conversation_id
    const restored = data.messages.map(message => ({
      message_id: message.message_id,
      role: message.role === 'assistant' ? 'ai' : message.role,
      content: message.content,
      evidences: message.metadata && message.metadata.evidences
        ? message.metadata.evidences : []
    }))
    messages.value = [createWelcomeMessage(), ...restored]
    const latestWithEvidence = [...restored].reverse().find(
      message => message.evidences && message.evidences.length)
    if (latestWithEvidence) {
      await setEvidences(latestWithEvidence.evidences)
      contextMode.value = 'evidence'
    }
  } catch (error) {
    workspace.clearConversation(projectId.value, activeAgent.value)
    conversationId.value = ''
  }
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
  previewLabel.value = ''
  activeDocumentId.value = ''
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
  contextMode.value = 'evidence'
  clearPreview()
  if (!evidence) return
  const version = previewLoadVersion
  try {
    const basePath = evidence.source_type === 'STANDARD_DOCUMENT'
      ? '/standards/documents/' + evidence.file_id
      : '/projects/' + projectId.value + '/documents/' + evidence.file_id
    let blobUrl
    try {
      blobUrl = await fetchProtectedBlobUrl(basePath + '/preview')
    } catch (previewError) {
      blobUrl = await fetchProtectedBlobUrl(basePath + '/file')
    }
    if (version !== previewLoadVersion) {
      URL.revokeObjectURL(blobUrl)
      return
    }
    previewBlobUrl = blobUrl
    previewUrl.value = blobUrl + '#page=' + evidence.page
    previewLabel.value = evidence.file_name + ' · 第 ' + evidence.page + ' 页'
    activeDocumentId.value = evidence.file_id
    if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
  } catch (e) {
    ElMessage.error('无法打开证据文件：' + e.message)
  }
}

async function focusMessageEvidence(message, index) {
  if (message.evidences && message.evidences.length) await setEvidences(message.evidences)
  await focusEvidence(index)
}

async function previewProjectDocument(doc) {
  contextMode.value = 'files'
  clearPreview()
  const version = previewLoadVersion
  try {
    let blobUrl
    const basePath = doc.source_type === 'STANDARD_DOCUMENT'
      ? '/standards/documents/' + doc.document_id
      : '/projects/' + projectId.value + '/documents/' + doc.document_id
    try {
      blobUrl = await fetchProtectedBlobUrl(basePath + '/preview')
    } catch (previewError) {
      blobUrl = await fetchProtectedBlobUrl(basePath + '/file')
    }
    if (version !== previewLoadVersion) {
      URL.revokeObjectURL(blobUrl)
      return
    }
    previewBlobUrl = blobUrl
    previewUrl.value = blobUrl
    previewLabel.value = doc.file_name
    activeDocumentId.value = doc.document_id
    if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
  } catch (e) {
    ElMessage.error('无法打开项目文件：' + e.message)
  }
}

function openPreview() {
  if (previewUrl.value) window.open(previewUrl.value, '_blank', 'noopener,noreferrer')
}

function openEvidencePanel() {
  contextMode.value = 'evidence'
  if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
}

function newConversation() {
  window.clearTimeout(planPollTimer)
  planTask.value = null
  planAnswerMessage = null
  workspace.clearConversation(projectId.value, activeAgent.value)
  conversationId.value = ''
  resetConversationView()
}

function resetConversationView() {
  window.clearTimeout(planPollTimer)
  planDecisionOpen.value = false
  planTask.value = null
  planAnswerMessage = null
  messages.value = [createWelcomeMessage()]
  question.value = ''
  thinking.value = false
  ++evidenceLoadVersion
  revokeEvidenceUrls()
  evidences.value = []
  activeEv.value = -1
  clearPreview()
}

function handleAssistantAction(action) {
  if (action.disabled) {
    ElMessage.info(action.label + ' Agent 后端尚未开放')
    return
  }
  if (action.id === 'standard') {
    selectAgent('standard')
    return
  }
  if (action.id === 'plan') {
    selectAgent('plan')
    return
  }
  messages.value.push({ role: 'user', content: action.label })
  messages.value.push({
    role: 'ai',
    content: '请直接输入项目名称、所在地区或项目类型，我会为您推荐最可能的项目。'
  })
  nextTick(scrollToBottom)
}

function planStageMessage(task) {
  const labels = {
    queued: '方案任务已排队', processing: '正在检索依据并生成方案',
    template_confirmation: '等待确认企业模板',
    outline_confirmation: '等待确认方案目录',
    final_review: '等待专业人员最终审核', completed: '方案文档已生成',
    failed: '方案任务失败', cancelled: '方案任务已取消'
  }
  return labels[task.current_stage] || '方案任务处理中'
}

function ensurePlanMessage() {
  if (planAnswerMessage && messages.value.includes(planAnswerMessage)) return planAnswerMessage
  planAnswerMessage = { role: 'ai', content: '', evidences: [], planDownloads: null }
  messages.value.push(planAnswerMessage)
  return planAnswerMessage
}

async function syncPlanTask(task) {
  planTask.value = task
  const message = ensurePlanMessage()
  stage.value = planStageMessage(task)
  const taskEvidences = [
    ...(task.project_evidences || []), ...(task.standard_evidences || [])
  ]
  if (taskEvidences.length) {
    message.evidences = taskEvidences
    await setEvidences(taskEvidences)
    contextMode.value = 'evidence'
  }
  if (task.status === 'WAITING_HUMAN') {
    message.content = planStageMessage(task) + '。'
    selectedTemplateId.value = task.human_payload.templates && task.human_payload.templates.length
      ? task.human_payload.templates[0].document_id : '__generic__'
    planOutline.value = [...(task.human_payload.outline || task.outline || [])]
    planComment.value = ''
    planDecisionOpen.value = true
  } else if (task.status === 'COMPLETED') {
    planDecisionOpen.value = false
    message.content = task.final_content || '施工方案已完成审核并生成文档。'
    message.planDownloads = task.download_urls || null
  } else if (task.status === 'FAILED' || task.status === 'CANCELLED') {
    planDecisionOpen.value = false
    message.content = task.status === 'CANCELLED'
      ? '方案任务已取消。' : '方案任务失败：' + (task.error || '未知错误')
  } else {
    message.content = planStageMessage(task) + '，当前进度 ' + task.progress + '%。'
  }
  await scrollToBottom()
}

async function pollPlanTask(taskId) {
  window.clearTimeout(planPollTimer)
  const task = await request('GET', '/projects/' + projectId.value + '/tasks/' + taskId)
  await syncPlanTask(task)
  if (['PENDING', 'RUNNING'].includes(task.status)) {
    planPollTimer = window.setTimeout(() => {
      pollPlanTask(taskId).catch(error => {
        ensurePlanMessage().content = '任务状态更新失败：' + error.message
      })
    }, 1000)
  }
}

async function startPlanTask(query) {
  planDecisionOpen.value = false
  planAnswerMessage = null
  const task = await request('POST', '/projects/' + projectId.value + '/plans', {
    request: query
  })
  await syncPlanTask(task)
  await pollPlanTask(task.task_id)
}

async function loadLatestPlanTask() {
  try {
    const data = await request('GET', '/projects/' + projectId.value + '/tasks?limit=1')
    if (!data.items || !data.items.length) return
    planAnswerMessage = null
    const task = await request(
      'GET', '/projects/' + projectId.value + '/tasks/' + data.items[0].task_id)
    await syncPlanTask(task)
    if (['PENDING', 'RUNNING'].includes(task.status)) await pollPlanTask(task.task_id)
  } catch (error) {
    ElMessage.error('无法恢复方案任务：' + error.message)
  }
}

async function submitPlanDecision(action) {
  if (!planTask.value || planDecisionLoading.value) return
  if (action === 'return_modify' && !planComment.value.trim()) {
    ElMessage.warning('请填写具体修改意见')
    return
  }
  const payload = { action, comment: planComment.value.trim() }
  if (action === 'select_template') payload.template_id = selectedTemplateId.value
  if (action === 'confirm' || action === 'return_modify') {
    payload.outline = planOutline.value.map(item => item.trim()).filter(Boolean)
  }
  planDecisionLoading.value = true
  try {
    const task = await request(
      'POST', '/projects/' + projectId.value + '/tasks/' + planTask.value.task_id + '/resume',
      payload)
    planDecisionOpen.value = false
    await syncPlanTask(task)
    await pollPlanTask(task.task_id)
  } catch (error) {
    ElMessage.error('方案任务恢复失败：' + error.message)
  } finally {
    planDecisionLoading.value = false
  }
}

async function openPlanDocument(path) {
  if (!path) return
  try {
    const blobUrl = await fetchProtectedBlobUrl(path)
    window.open(blobUrl, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)
  } catch (error) {
    ElMessage.error('无法打开方案文档：' + error.message)
  }
}

async function findProjectCandidates(query) {
  if (query.length < 2) return []
  try {
    const data = await request(
      'GET', '/projects/suggestions?q=' + encodeURIComponent(query) + '&limit=3')
    return data.items || []
  } catch (error) {
    return []
  }
}

async function routeInput(query) {
  return request('POST', '/assistant/route', {
    query, active_agent: activeAgent.value
  })
}

function appendRoutedReply(decision) {
  messages.value.push({
    role: 'ai',
    content: decision.answer || '',
    projects: decision.projects && decision.projects.length
      ? decision.projects : undefined
  })
}

async function ask() {
  const query = question.value.trim()
  if (!query || thinking.value) return
  messages.value.push({ role: 'user', content: query })
  question.value = ''
  thinking.value = true
  stage.value = '正在理解你的需求'
  await scrollToBottom()
  let decision = null
  try {
    decision = await routeInput(query)
  } catch (error) {
    const projectCandidates = await findProjectCandidates(query)
    if (projectCandidates.length) {
      decision = {
        type: 'PROJECT_SUGGESTIONS',
        answer: '我找到了以下可能相关的项目。请选择一个项目，确认后我会锁定知识库，并在右侧显示该项目的全部资料。',
        projects: projectCandidates
      }
    }
  }
  if (decision && decision.type !== 'AGENT_ROUTE') {
    appendRoutedReply(decision)
    thinking.value = false
    await scrollToBottom()
    return
  }
  if (decision && decision.type === 'AGENT_ROUTE' && !decision.available) {
    appendRoutedReply(decision)
    thinking.value = false
    await scrollToBottom()
    return
  }
  const targetAgent = decision && ['standard', 'plan'].includes(decision.intent)
    ? decision.intent : activeAgent.value
  if (targetAgent !== activeAgent.value) {
    activeAgent.value = targetAgent
    conversationId.value = workspace.getConversation(
      projectId.value, activeAgent.value)
    selectedFolderId.value = ''
  }
  if (activeAgent.value === 'plan') {
    try {
      await startPlanTask(query)
    } catch (error) {
      messages.value.push({ role: 'ai', content: '方案任务创建失败：' + error.message })
    } finally {
      thinking.value = false
      await scrollToBottom()
    }
    return
  }
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
    const stream = activeAgent.value === 'standard'
      ? streamStandardQuery : streamQuery
    await stream(projectId.value, query, (event, data) => {
      if (event === 'stage') stage.value = data.message
      if (event === 'started' && data.conversation_id) {
        conversationId.value = data.conversation_id
        workspace.setConversation(
          projectId.value, data.conversation_id, activeAgent.value)
      }
      if (event === 'evidence') {
        answerMessage.evidences = data.evidences
        setEvidences(data.evidences)
        contextMode.value = 'evidence'
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
    }, topK.value, conversationId.value || null)
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
  if (activeAgent.value === 'standard') {
    standardUploadOptions.value = options
    Object.assign(standardForm, createStandardForm(options.file.name))
    standardUploadOpen.value = true
    return
  }
  try {
    const data = await uploadDocument(
      projectId.value, options.file, selectedFolderId.value)
    options.onSuccess(data)
    contextMode.value = 'files'
    await loadDocuments()
    ElMessage.success('已上传：' + data.file_name)
  } catch (e) {
    options.onError(e)
    ElMessage.error('上传失败：' + e.message)
  }
}

function createStandardForm(fileName = '') {
  return {
    standard_name: fileName.replace(/\.[^.]+$/, ''), standard_code: '',
    version: '', region: '全国', discipline: '', standard_type: '国家标准',
    status: 'unknown', publish_date: '', effective_date: ''
  }
}

function cancelStandardUpload() {
  standardUploadOpen.value = false
  if (standardUploadOptions.value) {
    standardUploadOptions.value.onError(new Error('cancelled'))
  }
  standardUploadOptions.value = null
}

async function submitStandardUpload() {
  if (!standardForm.standard_name.trim() || !standardUploadOptions.value) {
    ElMessage.warning('请填写规范名称')
    return
  }
  standardUploading.value = true
  try {
    const data = await uploadStandardDocument(
      standardUploadOptions.value.file, standardForm)
    standardUploadOptions.value.onSuccess(data)
    standardUploadOpen.value = false
    standardUploadOptions.value = null
    contextMode.value = 'files'
    await loadStandards()
    ElMessage.success('规范已上传并进入解析队列')
  } catch (error) {
    standardUploadOptions.value.onError(error)
    ElMessage.error('规范上传失败：' + error.message)
  } finally {
    standardUploading.value = false
  }
}

async function selectAgent(agent) {
  navigationOpen.value = false
  if (agent === activeAgent.value) return
  activeAgent.value = agent
  selectedFolderId.value = ''
  conversationId.value = ''
  resetConversationView()
  await loadConversation()
}

async function createFolder(payload) {
  try {
    await request('POST', '/projects/' + projectId.value + '/folders', payload)
    await loadFolders()
    ElMessage.success(payload.parent_id ? '子文件夹已创建' : '文件夹已创建')
  } catch (e) {
    ElMessage.error('创建失败：' + e.message)
  }
}

async function renameFolder({ folder, name }) {
  try {
    await request('PATCH', '/projects/' + projectId.value + '/folders/' + folder.folder_id, { name })
    await loadFolders()
    ElMessage.success('文件夹已重命名')
  } catch (e) {
    ElMessage.error('重命名失败：' + e.message)
  }
}

async function deleteFolder(folder) {
  try {
    await request('DELETE', '/projects/' + projectId.value + '/folders/' + folder.folder_id)
    await loadFolders()
    ElMessage.success('文件夹已删除')
  } catch (e) {
    ElMessage.error('删除失败：' + e.message)
  }
}

function selectSuggestedProject(project) {
  projectQuery.value = ''
  lockProject(project)
}

async function createProject() {
  if (!projectForm.name.trim() || projectCreating.value) return
  projectCreating.value = true
  try {
    const project = await request('POST', '/projects', {
      name: projectForm.name.trim(),
      description: projectForm.description.trim()
    })
    projects.value = [project, ...projects.value]
    projectCreateOpen.value = false
    projectPickerOpen.value = false
    projectForm.name = ''
    projectForm.description = ''
    workspace.rememberProject(project.project_id)
    await router.push('/projects/' + project.project_id)
  } catch (error) {
    ElMessage.error('项目创建失败：' + error.message)
  } finally {
    projectCreating.value = false
  }
}

function chooseProjectFromChat(project) {
  lockProject(project, true)
}

function lockProject(project, fromChat = false) {
  projectPickerOpen.value = false
  navigationOpen.value = false
  if (project.project_id !== projectId.value) {
    router.push({ path: '/projects/' + project.project_id,
                  query: fromChat ? { selected: '1' } : {} })
  } else if (fromChat) {
    contextMode.value = 'files'
    messages.value.push({
      role: 'ai', content: '已锁定“' + project.name + '”，右侧已显示该项目的全部资料。'
    })
  }
}

function logout() {
  auth.logout()
  router.push('/login')
}

watch(projectId, async () => {
  window.clearTimeout(documentPollTimer)
  selectedFolderId.value = ''
  resetConversationView()
  try {
    await loadWorkspace()
    if (route.query.selected === '1') {
      contextMode.value = 'files'
      if (window.innerWidth <= 1040) evidenceDrawerOpen.value = true
      messages.value.push({
        role: 'ai',
        content: '已锁定“' + currentProject.value.name + '”，右侧已显示该项目的全部资料。'
      })
      router.replace({ path: route.path })
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}, { immediate: true })

onBeforeUnmount(() => {
  window.clearTimeout(documentPollTimer)
  window.clearTimeout(planPollTimer)
  ++evidenceLoadVersion
  revokeEvidenceUrls()
  clearPreview()
})
</script>

<style scoped>
.workspace { --topbar-height: 56px; height: 100vh; background: #eef1f5; color: #24303c; overflow: hidden; }
.workspace-body { height: calc(100vh - var(--topbar-height)); display: grid; grid-template-columns: 252px minmax(520px, 1fr) 340px; }
.conversation-panel { min-width: 0; display: grid; grid-template-rows: 64px minmax(0, 1fr) auto; background: #fff; }
.conversation-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 24px; border-bottom: 1px solid #e2e6ea; }
.conversation-title { min-width: 0; }
.agent-label { color: #1f5fbf; font-size: 11px; font-weight: 700; }
.conversation-title h1 { margin: 3px 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 16px; letter-spacing: 0; }
.knowledge-status { display: flex; align-items: center; gap: 6px; color: #617080; font-size: 11px; white-space: nowrap; }
.knowledge-status :deep(.el-icon) { color: #25855a; }
.knowledge-status strong { color: #2d3748; }
.conversation-scroll { min-height: 0; overflow-y: auto; background: #f8fafc; }
.message-list { width: min(860px, calc(100% - 44px)); margin: 0 auto; padding: 28px 0 80px; }
.message { display: grid; grid-template-columns: 108px minmax(0, 1fr); gap: 14px; padding: 18px 0; border-bottom: 1px solid #e4e8ed; }
.message-author { color: #667085; font-size: 12px; font-weight: 600; }
.message-content { min-width: 0; color: #263445; font-size: 14px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.message.user .message-content { color: #17202a; font-weight: 500; }
.citation { display: inline-grid; place-items: center; min-width: 25px; height: 20px; margin: 0 2px; padding: 0 5px; border: 1px solid #8eb0df; border-radius: 4px; background: #edf4ff; color: #174ea6; cursor: pointer; font-size: 11px; vertical-align: 1px; }
.citation:hover { background: #dbe9fb; }
.assistant-actions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 16px; }
.assistant-actions button { min-width: 0; min-height: 48px; display: flex; align-items: center; gap: 7px; padding: 8px 10px; border: 1px solid #d4dce7; border-radius: 6px; background: #fff; color: #344054; cursor: pointer; text-align: left; }
.assistant-actions button:hover:not(:disabled) { border-color: #7698c8; background: #f3f7fc; color: #174ea6; }
.assistant-actions button:disabled { color: #98a2b3; cursor: not-allowed; }
.assistant-actions button span { min-width: 0; flex: 1; font-size: 12px; }
.assistant-actions button small { color: #98a2b3; font-size: 9px; white-space: nowrap; }
.project-suggestions { display: flex; flex-direction: column; gap: 7px; margin-top: 14px; }
.project-suggestions > button { width: 100%; min-height: 58px; display: grid; grid-template-columns: 34px minmax(0, 1fr) 16px; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid #d4dce7; border-radius: 6px; background: #fff; color: #344054; cursor: pointer; text-align: left; }
.project-suggestions > button:hover { border-color: #7698c8; background: #f3f7fc; }
.suggestion-folder { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 5px; background: #eaf1fb; color: #1f5fbf; }
.project-suggestions > button > span:nth-child(2) { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.project-suggestions strong, .project-suggestions small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-suggestions strong { font-size: 12px; }
.project-suggestions small { color: #7a8594; font-size: 10px; }
.fallback { margin-top: 10px; padding-left: 9px; border-left: 3px solid #d69e2e; color: #8a5a12; }
.plan-downloads { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.decision-message { margin: 0 0 16px; color: #52606d; line-height: 1.6; }
.template-options { width: 100%; display: flex; flex-direction: column; align-items: stretch; gap: 8px; }
.template-options :deep(.el-radio) { width: 100%; height: auto; min-height: 40px; margin: 0; padding: 9px 12px; }
.outline-editor { max-height: 420px; overflow-y: auto; }
.outline-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) 34px; align-items: center; gap: 8px; margin-bottom: 8px; }
.outline-row > span { color: #7a8594; font-size: 12px; text-align: right; }
.review-warnings { margin: 14px 0; padding: 12px 0; border-bottom: 1px solid #e2e6ea; }
.review-warnings ul { max-height: 160px; margin: 8px 0 0; padding-left: 20px; overflow-y: auto; color: #7a4b16; font-size: 12px; line-height: 1.7; }
.plan-preview { margin-top: 14px; border-top: 1px solid #e2e6ea; padding-top: 12px; }
.plan-preview summary { color: #1f5fbf; cursor: pointer; font-size: 13px; }
.plan-preview pre { max-height: 360px; margin: 10px 0 0; padding: 12px; overflow: auto; background: #f6f8fa; color: #344054; font: inherit; font-size: 12px; line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
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
.setting-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 0; border-bottom: 1px solid #e5e8ec; }
.setting-row > div { display: flex; flex-direction: column; gap: 5px; }
.setting-row strong, .setting-title strong { font-size: 13px; }
.setting-row span, .setting-title span { color: #7a8594; font-size: 11px; }
.setting-block { padding: 18px 0; }
.setting-title { display: flex; justify-content: space-between; margin-bottom: 14px; }
.standard-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
.standard-form-grid .span-two { grid-column: 1 / -1; }
.standard-form-grid :deep(.el-select), .standard-form-grid :deep(.el-date-editor) { width: 100%; }
.compact .message { padding: 11px 0; }
.compact .message-list { padding-top: 16px; }
.compact .conversation-header { height: 52px; }
@keyframes pulse { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
@media (max-width: 1280px) {
  .workspace-body { grid-template-columns: 224px minmax(480px, 1fr) 300px; }
}
@media (max-width: 1040px) {
  .workspace-body { grid-template-columns: 224px minmax(0, 1fr); }
  .desktop-evidence { display: none; }
}
@media (max-width: 760px) {
  .workspace-body { grid-template-columns: minmax(0, 1fr); }
  .desktop-navigation { display: none; }
  .conversation-header { padding: 0 14px; }
  .knowledge-status span { display: none; }
  .message-list { width: calc(100% - 28px); }
  .message { grid-template-columns: 1fr; gap: 5px; }
  .assistant-actions { grid-template-columns: 1fr; }
  .composer { margin: 0 10px 10px; }
  .standard-form-grid { grid-template-columns: 1fr; }
  .standard-form-grid .span-two { grid-column: auto; }
}
</style>
