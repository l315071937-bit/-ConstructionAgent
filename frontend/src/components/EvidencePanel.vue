<template>
  <aside class="context-panel">
    <div class="panel-header">
      <div>
        <h3>项目工作区</h3>
        <span>{{ project ? project.name : '尚未选择项目' }}</span>
      </div>
      <el-upload :show-file-list="false" :http-request="upload" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt">
        <el-button circle size="small" type="primary" title="上传项目资料">
          <el-icon><Upload /></el-icon>
        </el-button>
      </el-upload>
    </div>

    <div class="panel-tabs" role="tablist" aria-label="项目工作区视图">
      <button type="button" :class="{ active: mode === 'files' }" @click="setMode('files')">
        项目文件 <span>{{ documents.length }}</span>
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
            <strong>{{ doc.file_name }}</strong>
            <small>{{ doc.page_count }} 页 · {{ statusLabel(doc.parse_status) }}</small>
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
      <el-empty v-else :description="documents.length ? '没有匹配的项目文件' : '当前项目暂无资料'" :image-size="60" />
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
            <strong>{{ ev.file_name }}</strong>
            <span>第 {{ ev.page }} 页</span>
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
import { ArrowRight, Document, Search, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  activeDocumentId: { type: String, default: '' },
  activeIndex: { type: Number, default: -1 },
  documents: { type: Array, default: () => [] },
  evidences: { type: Array, default: () => [] },
  mode: { type: String, default: 'files' },
  previewLabel: { type: String, default: '' },
  previewUrl: { type: String, default: '' },
  project: { type: Object, default: null }
})

const emit = defineEmits([
  'focus-evidence', 'open-preview', 'open-project-document', 'update:mode', 'upload'
])
const fileQuery = ref('')
const fileTypeFilter = ref('')
const fileTypes = computed(() => [...new Set(
  props.documents.map(doc => fileType(doc.file_name)))].sort())
const filteredDocuments = computed(() => {
  const query = fileQuery.value.trim().toLowerCase()
  return props.documents.filter(doc =>
    (!query || doc.file_name.toLowerCase().includes(query)) &&
    (!fileTypeFilter.value || fileType(doc.file_name) === fileTypeFilter.value))
})

function fileType(fileName) {
  const extension = fileName.split('.').pop()
  return extension ? extension.slice(0, 4).toUpperCase() : 'FILE'
}

function statusLabel(status) {
  return { PENDING: '等待处理', PARSING: '解析中', READY: '可检索', FAILED: '解析失败' }[status] || status
}

function setMode(value) {
  emit('update:mode', value)
}

function upload(options) {
  emit('upload', options)
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
