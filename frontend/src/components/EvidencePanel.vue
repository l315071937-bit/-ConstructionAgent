<template>
  <aside class="context-panel">
    <div class="panel-header">
      <div>
        <h3>{{ workspaceTitle }}</h3>
        <span>{{ project ? project.name : '尚未选择项目' }}</span>
      </div>
      <el-upload v-if="canUpload" :show-file-list="false" :http-request="upload" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt">
        <el-button circle size="small" type="primary" :title="uploadTitle">
          <el-icon><Upload /></el-icon>
        </el-button>
      </el-upload>
    </div>

    <div class="panel-tabs" role="tablist" aria-label="项目工作区视图">
      <button type="button" :class="{ active: mode === 'files' }" @click="setMode('files')">
        {{ libraryLabel }} <span>{{ documents.length }}</span>
      </button>
      <button type="button" :class="{ active: mode === 'evidence' }" @click="setMode('evidence')">
        检索依据 <span>{{ evidences.length }}</span>
      </button>
    </div>

    <div v-if="previewUrl" class="preview-panel">
      <div class="preview-head">
        <span :title="previewLabel">{{ previewLabel || '文件预览' }}</span>
        <el-button link type="primary" @click="$emit('open-preview')">新窗口打开</el-button>
      </div>
      <iframe :src="previewUrl" class="pdf" title="项目文件预览"></iframe>
    </div>

    <template v-if="mode === 'files'">
      <div v-if="showFolders" class="folder-toolbar">
        <button type="button" :class="{ active: !selectedFolderId }" @click="$emit('select-folder', '')">
          <el-icon><FolderOpened /></el-icon>
          <span>全部文件</span>
          <small>{{ documents.length }}</small>
        </button>
        <el-button circle size="small" title="新建文件夹" @click="promptCreateFolder(null)">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div v-if="showFolders && flatFolders.length" class="folder-tree">
        <div v-for="folder in flatFolders" :key="folder.folder_id" class="folder-row"
             :class="{ active: folder.folder_id === selectedFolderId }"
             :style="{ paddingLeft: (8 + folder.depth * 16) + 'px' }">
          <button type="button" class="folder-select" @click="$emit('select-folder', folder.folder_id)">
            <el-icon><Folder /></el-icon>
            <span :title="folder.name">{{ folder.name }}</span>
          </button>
          <el-dropdown trigger="click" @command="command => handleFolderCommand(command, folder)">
            <button type="button" class="folder-menu" title="文件夹操作" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="create">新建子文件夹</el-dropdown-item>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item command="delete" divided>删除空文件夹</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <div class="file-toolbar">
        <el-input v-model="fileQuery" clearable size="small" placeholder="搜索当前项目文件">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="fileTypeFilter" size="small" placeholder="全部" aria-label="文件类型">
          <el-option label="全部" value="" />
          <el-option v-for="type in fileTypes" :key="type" :label="type" :value="type" />
        </el-select>
      </div>
      <div v-if="filteredDocuments.length" class="document-list">
        <button v-for="doc in filteredDocuments" :key="doc.document_id" class="document-item" type="button"
                :class="{ active: doc.document_id === activeDocumentId }"
                @click="$emit('open-project-document', doc)">
          <span class="file-badge">{{ fileType(doc.file_name) }}</span>
          <span class="document-copy">
            <strong>{{ documentTitle(doc) }}</strong>
            <small>{{ documentMeta(doc) }}</small>
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
      <el-empty v-else :description="emptyDescription" :image-size="60" />
    </template>

    <template v-else>
      <div v-if="evidences.length" class="evidence-list">
        <button v-for="(ev, i) in evidences" :key="ev.evidence_id || i" class="evidence-item"
                :class="{ active: i === activeIndex }" type="button" @click="$emit('focus-evidence', i + 1)">
          <div class="thumbnail-wrap">
            <img v-if="ev.thumbnail_blob_url" :src="ev.thumbnail_blob_url" class="thumbnail" alt="" />
            <div v-else class="thumbnail-placeholder"><el-icon><Document /></el-icon></div>
            <span class="evidence-number">E{{ i + 1 }}</span>
          </div>
          <div class="evidence-meta">
            <strong>{{ evidenceTitle(ev) }}</strong>
            <span>{{ evidenceMeta(ev) }}</span>
            <el-progress :percentage="Math.round(ev.score * 100)" :show-text="false" :stroke-width="3" />
          </div>
        </button>
      </div>
      <el-empty v-else description="对话检索后将在这里显示引用依据" :image-size="60" />
    </template>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { ArrowRight, Document, Folder, FolderOpened, MoreFilled, Plus, Search, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  activeDocumentId: { type: String, default: '' },
  activeIndex: { type: Number, default: -1 },
  canUpload: { type: Boolean, default: true },
  documents: { type: Array, default: () => [] },
  evidences: { type: Array, default: () => [] },
  folders: { type: Array, default: () => [] },
  libraryLabel: { type: String, default: '项目文件' },
  mode: { type: String, default: 'files' },
  previewLabel: { type: String, default: '' },
  previewUrl: { type: String, default: '' },
  project: { type: Object, default: null },
  selectedFolderId: { type: String, default: '' },
  showFolders: { type: Boolean, default: true },
  uploadTitle: { type: String, default: '上传项目资料' },
  workspaceTitle: { type: String, default: '项目工作区' }
})

const emit = defineEmits([
  'create-folder', 'delete-folder', 'focus-evidence', 'open-preview',
  'open-project-document', 'rename-folder', 'select-folder', 'update:mode', 'upload'
])
const fileQuery = ref('')
const fileTypeFilter = ref('')
const fileTypes = computed(() => [...new Set(
  props.documents.map(doc => fileType(doc.file_name)))].sort())
const flatFolders = computed(() => {
  const children = new Map()
  for (const folder of props.folders) {
    const key = folder.parent_id || ''
    if (!children.has(key)) children.set(key, [])
    children.get(key).push(folder)
  }
  for (const values of children.values()) {
    values.sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
  }
  const result = []
  const visited = new Set()
  function append(parentId, depth) {
    for (const folder of children.get(parentId) || []) {
      if (visited.has(folder.folder_id)) continue
      visited.add(folder.folder_id)
      result.push({ ...folder, depth })
      append(folder.folder_id, depth + 1)
    }
  }
  append('', 0)
  for (const folder of props.folders) {
    if (!visited.has(folder.folder_id)) result.push({ ...folder, depth: 0 })
  }
  return result
})
const filteredDocuments = computed(() => {
  const query = fileQuery.value.trim().toLowerCase()
  return props.documents.filter(doc =>
    (!props.selectedFolderId || doc.folder_id === props.selectedFolderId) &&
    (!query || doc.file_name.toLowerCase().includes(query)) &&
    (!fileTypeFilter.value || fileType(doc.file_name) === fileTypeFilter.value))
})
const emptyDescription = computed(() => {
  if (props.selectedFolderId) return '当前文件夹暂无资料'
  return props.documents.length ? '没有匹配的项目文件' : '当前项目暂无资料'
})

function fileType(fileName) {
  const extension = fileName.split('.').pop()
  return extension ? extension.slice(0, 4).toUpperCase() : 'FILE'
}

function statusLabel(status) {
  return { PENDING: '等待处理', PARSING: '解析中', READY: '可检索', FAILED: '解析失败' }[status] || status
}

function documentTitle(document) {
  if (document.source_type === 'STANDARD_DOCUMENT') {
    return [document.standard_code, document.standard_name].filter(Boolean).join(' · ')
  }
  return document.file_name
}

function documentMeta(document) {
  if (document.source_type === 'STANDARD_DOCUMENT') {
    const status = {
      active: '现行', repealed: '废止', replaced: '被替代',
      upcoming: '即将实施', unknown: '状态未知'
    }[document.status] || '状态未知'
    return [document.region, document.version, status].filter(Boolean).join(' · ')
  }
  return document.page_count + ' 页 · ' + statusLabel(document.parse_status)
}

function evidenceTitle(evidence) {
  if (evidence.source_type === 'STANDARD_DOCUMENT') {
    return [evidence.standard_code, evidence.standard_name].filter(Boolean).join(' · ')
  }
  return evidence.file_name
}

function evidenceMeta(evidence) {
  if (evidence.source_type === 'STANDARD_DOCUMENT') {
    return [evidence.article ? '第 ' + evidence.article + ' 条' : '',
      '第 ' + evidence.page + ' 页'].filter(Boolean).join(' · ')
  }
  return '第 ' + evidence.page + ' 页'
}

function setMode(value) {
  emit('update:mode', value)
}

function upload(options) {
  emit('upload', options)
}

async function promptCreateFolder(parentId) {
  try {
    const { value } = await ElMessageBox.prompt(
      parentId ? '输入子文件夹名称' : '输入文件夹名称',
      parentId ? '新建子文件夹' : '新建文件夹',
      { inputPattern: /\S+/, inputErrorMessage: '请输入文件夹名称' })
    emit('create-folder', { name: value.trim(), parent_id: parentId })
  } catch (error) { /* user cancelled */ }
}

async function handleFolderCommand(command, folder) {
  if (command === 'create') return promptCreateFolder(folder.folder_id)
  if (command === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt(
        '输入新的文件夹名称', '重命名',
        { inputValue: folder.name, inputPattern: /\S+/,
          inputErrorMessage: '请输入文件夹名称' })
      emit('rename-folder', { folder, name: value.trim() })
    } catch (error) { /* user cancelled */ }
    return
  }
  if (command === 'delete') {
    try {
      await ElMessageBox.confirm(
        '确定删除空文件夹“' + folder.name + '”吗？', '删除文件夹',
        { type: 'warning' })
      emit('delete-folder', folder)
    } catch (error) { /* user cancelled */ }
  }
}
</script>

<style scoped>
.context-panel { height: 100%; display: flex; flex-direction: column; min-width: 0; border-left: 1px solid #dfe3e8; background: #fff; overflow: hidden; }
.panel-header { min-height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px 14px; border-bottom: 1px solid #e5e8ec; }
.panel-header > div { min-width: 0; }
.panel-header h3 { margin: 0; color: #25313c; font-size: 14px; }
.panel-header span { display: block; margin-top: 3px; overflow: hidden; color: #8a94a3; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.panel-tabs { height: 40px; display: grid; grid-template-columns: 1fr 1fr; padding: 0 10px; border-bottom: 1px solid #e5e8ec; }
.panel-tabs button { border: 0; border-bottom: 2px solid transparent; background: transparent; color: #667085; cursor: pointer; font-size: 12px; }
.panel-tabs button.active { border-bottom-color: #2166d1; color: #174ea6; font-weight: 600; }
.panel-tabs span { margin-left: 3px; color: #98a2b3; font-size: 10px; }
.preview-panel { padding: 8px 10px 10px; border-bottom: 1px solid #e5e8ec; }
.preview-head { min-width: 0; display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 11px; font-weight: 600; }
.preview-head > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pdf { width: 100%; height: 300px; display: block; margin-top: 6px; border: 0; background: #f4f6f8; }
.folder-toolbar { min-height: 40px; display: grid; grid-template-columns: minmax(0, 1fr) 28px; align-items: center; gap: 6px; padding: 5px 10px; border-bottom: 1px solid #edf0f3; }
.folder-toolbar > button:first-child { min-width: 0; height: 30px; display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; align-items: center; gap: 6px; padding: 0 7px; border: 0; border-radius: 4px; background: transparent; color: #52606d; cursor: pointer; text-align: left; }
.folder-toolbar > button:first-child:hover, .folder-toolbar > button:first-child.active { background: #edf4fc; color: #174ea6; }
.folder-toolbar span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.folder-toolbar small { color: #98a2b3; font-size: 9px; }
.folder-tree { max-height: 190px; overflow: auto; padding: 4px 6px; border-bottom: 1px solid #edf0f3; }
.folder-row { min-width: 0; height: 30px; display: grid; grid-template-columns: minmax(0, 1fr) 26px; align-items: center; padding-right: 3px; border-radius: 4px; }
.folder-row:hover, .folder-row.active { background: #edf4fc; }
.folder-select { min-width: 0; height: 100%; display: flex; align-items: center; gap: 6px; padding: 0; border: 0; background: transparent; color: #52606d; cursor: pointer; text-align: left; }
.folder-row.active .folder-select { color: #174ea6; font-weight: 600; }
.folder-select span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.folder-menu { width: 24px; height: 24px; display: grid; place-items: center; padding: 0; border: 0; background: transparent; color: #7a8594; cursor: pointer; }
.file-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) 82px; gap: 6px; padding: 10px; border-bottom: 1px solid #edf0f3; }
.document-list, .evidence-list { flex: 1; min-height: 0; overflow-y: auto; padding: 8px 10px; }
.document-item { width: 100%; min-height: 56px; display: grid; grid-template-columns: 40px minmax(0, 1fr) 16px; align-items: center; gap: 9px; padding: 7px 6px; border: 0; border-bottom: 1px solid #e7eaee; background: transparent; color: #344054; cursor: pointer; text-align: left; }
.document-item:hover, .document-item.active { background: #f3f7fc; }
.file-badge { width: 38px; height: 30px; display: grid; place-items: center; border-radius: 4px; background: #edf1f5; color: #52606d; font-size: 9px; font-weight: 700; }
.document-copy { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.document-copy strong, .document-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.document-copy strong { font-size: 11px; }
.document-copy small { color: #8a94a3; font-size: 10px; }
.evidence-item { width: 100%; display: grid; grid-template-columns: 86px minmax(0, 1fr); gap: 9px; padding: 7px; margin-bottom: 7px; border: 1px solid #dfe3e8; border-radius: 6px; background: #fff; color: #344054; cursor: pointer; text-align: left; }
.evidence-item:hover, .evidence-item.active { border-color: #2f6fc7; background: #f9fbfe; }
.thumbnail-wrap { position: relative; width: 86px; aspect-ratio: 4 / 3; overflow: hidden; border-radius: 4px; background: #eef1f5; }
.thumbnail { width: 100%; height: 100%; display: block; object-fit: cover; }
.thumbnail-placeholder { width: 100%; height: 100%; display: grid; place-items: center; color: #98a2b3; font-size: 22px; }
.evidence-number { position: absolute; top: 4px; left: 4px; padding: 1px 5px; border-radius: 3px; background: rgba(24, 38, 56, .82); color: #fff; font-size: 10px; }
.evidence-meta { min-width: 0; display: flex; flex-direction: column; gap: 6px; padding-top: 2px; }
.evidence-meta strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.evidence-meta > span { color: #7a8594; font-size: 10px; }
</style>
