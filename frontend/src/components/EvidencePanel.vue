<template>
  <aside class="evidence-panel">
    <div class="panel-header">
      <div>
        <h3>检索依据</h3>
        <span>{{ evidences.length }} 条 Evidence</span>
      </div>
      <div class="panel-actions">
        <el-button circle size="small" title="项目资料" @click="$emit('documents')">
          <el-icon><FolderOpened /></el-icon>
        </el-button>
        <el-upload :show-file-list="false" :http-request="upload" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt">
          <el-button circle size="small" type="primary" title="上传资料">
            <el-icon><Upload /></el-icon>
          </el-button>
        </el-upload>
      </div>
    </div>

    <div v-if="previewUrl" class="preview-panel">
      <div class="preview-head">
        <span>当前证据</span>
        <el-button link type="primary" @click="$emit('open-preview')">新窗口打开</el-button>
      </div>
      <iframe :src="previewUrl" class="pdf"></iframe>
    </div>

    <div v-if="!evidences.length" class="empty-evidence">
      <el-empty description="等待检索依据" :image-size="64" />
      <div v-if="documents.length" class="source-summary">
        <div class="summary-title">项目资料</div>
        <div v-for="doc in documents.slice(0, 5)" :key="doc.document_id" class="source-row">
          <span>{{ doc.file_name }}</span>
          <el-tag size="small" :type="doc.parse_status === 'READY' ? 'success' : 'info'">
            {{ doc.parse_status === 'READY' ? '可检索' : '处理中' }}
          </el-tag>
        </div>
      </div>
    </div>

    <div v-else class="evidence-list">
      <button v-for="(ev, i) in evidences" :key="ev.evidence_id || i" class="evidence-item"
              :class="{ active: i === activeIndex }" type="button" @click="$emit('open-document', i + 1)">
        <div class="thumbnail-wrap">
          <img v-if="ev.thumbnail_blob_url" :src="ev.thumbnail_blob_url" class="thumbnail" />
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
  </aside>
</template>

<script setup>
import { Document, FolderOpened, Upload } from '@element-plus/icons-vue'

defineProps({
  activeIndex: { type: Number, default: -1 },
  documents: { type: Array, default: () => [] },
  evidences: { type: Array, default: () => [] },
  previewUrl: { type: String, default: '' }
})

const emit = defineEmits(['documents', 'open-document', 'open-preview', 'upload'])
function upload(options) {
  emit('upload', options)
}
</script>

<style scoped>
.evidence-panel { height: 100%; display: flex; flex-direction: column; min-width: 0; border-left: 1px solid #dfe3e8; background: #fff; overflow: hidden; }
.panel-header { min-height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 14px; border-bottom: 1px solid #e5e8ec; }
.panel-header h3 { margin: 0; color: #25313c; font-size: 14px; }
.panel-header span { color: #8a94a3; font-size: 11px; }
.panel-actions { display: flex; align-items: center; gap: 7px; }
.preview-panel { padding: 10px 12px; border-bottom: 1px solid #e5e8ec; }
.preview-head { display: flex; justify-content: space-between; align-items: center; font-size: 12px; font-weight: 600; }
.pdf { width: 100%; height: 260px; border: 0; margin-top: 8px; background: #f4f6f8; }
.empty-evidence { flex: 1; overflow-y: auto; padding: 8px 14px; }
.source-summary { border-top: 1px solid #e5e8ec; padding-top: 12px; }
.summary-title { margin-bottom: 8px; color: #667085; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.source-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 0; font-size: 11px; }
.source-row > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.evidence-list { flex: 1; overflow-y: auto; padding: 10px; }
.evidence-item { width: 100%; display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 10px; padding: 8px; margin-bottom: 8px; border: 1px solid #dfe3e8; border-radius: 6px; background: #fff; color: #344054; cursor: pointer; text-align: left; }
.evidence-item:hover { border-color: #94add2; background: #f9fbfe; }
.evidence-item.active { border-color: #2f6fc7; box-shadow: inset 3px 0 0 #2f6fc7; }
.thumbnail-wrap { position: relative; width: 92px; aspect-ratio: 4 / 3; overflow: hidden; border-radius: 4px; background: #eef1f5; }
.thumbnail { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumbnail-placeholder { width: 100%; height: 100%; display: grid; place-items: center; color: #98a2b3; font-size: 24px; }
.evidence-number { position: absolute; top: 4px; left: 4px; padding: 1px 5px; border-radius: 3px; background: rgba(24, 38, 56, .82); color: #fff; font-size: 10px; }
.evidence-meta { min-width: 0; display: flex; flex-direction: column; gap: 7px; padding-top: 2px; }
.evidence-meta strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.evidence-meta > span { color: #7a8594; font-size: 11px; }
</style>
