<template>
  <div class="chat-wrap">
    <el-header class="head">
      <el-button link @click="$router.push('/projects')">返回项目列表</el-button>
      <span class="title">项目对话</span>
      <el-upload :show-file-list="false" :http-request="doUpload" accept=".pdf,.doc,.docx,.xls,.xlsx,.txt">
        <el-button size="small" type="primary">上传资料</el-button>
      </el-upload>
    </el-header>
    <div class="body">
      <div class="chat">
        <div v-for="(m, i) in messages" :key="i" class="msg">
          <div v-if="m.role === 'user'" class="bubble user">{{ m.content }}</div>
          <div v-else class="bubble ai">
            <span v-for="(seg, j) in renderAnswer(m.content)" :key="j">
              <el-tag v-if="seg.ref" size="small" type="primary" class="ref"
                      @click="focusEvidence(seg.ref)">E{{ seg.ref }}</el-tag>
              <span v-else>{{ seg.text }}</span>
            </span>
            <div v-if="m.fallback" class="fallback">未找到足够证据，建议人工查看相关图纸/文档。</div>
          </div>
        </div>
        <div v-if="thinking" class="msg"><div class="bubble ai dim">{{ stage }}</div></div>
      </div>
      <div class="evidence">
        <h4>检索依据</h4>
        <el-empty v-if="!evidences.length" description="暂无证据" :image-size="60" />
        <div v-for="(ev, i) in evidences" :key="i" class="ev-card" :class="{ active: i === activeEv }"
             @click="focusEvidence(i + 1)">
          <img v-if="ev.thumbnail_url" :src="ev.thumbnail_url" class="thumb" />
          <div class="ev-meta">
            <div class="ev-file">{{ ev.file_name }}</div>
            <div class="ev-page">第 {{ ev.page }} 页 · score {{ ev.score }}</div>
          </div>
        </div>
        <iframe v-if="pdfUrl" :src="pdfUrl" class="pdf"></iframe>
      </div>
    </div>
    <div class="input-bar">
      <el-input v-model="question" placeholder="输入工程问题，如：配电箱安装有什么要求？" @keyup.enter="ask" />
      <el-button type="primary" :disabled="!question || thinking" @click="ask">发送</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { streamQuery, uploadDocument } from '../api/client'

const route = useRoute()
const projectId = route.params.id
const messages = ref([])
const evidences = ref([])
const question = ref('')
const thinking = ref(false)
const stage = ref('')
const activeEv = ref(-1)
const pdfUrl = ref('')

function renderAnswer(text) {
  const segs = []
  const re = /\[E(\d+)\]/g
  let last = 0
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) segs.push({ text: text.slice(last, m.index) })
    segs.push({ ref: Number(m[1]) })
    last = m.index + m[0].length
  }
  if (last < text.length) segs.push({ text: text.slice(last) })
  return segs
}

function focusEvidence(n) {
  activeEv.value = n - 1
  const ev = evidences.value[n - 1]
  if (ev) pdfUrl.value = ev.thumbnail_url + '?width=800'
}

async function ask() {
  const q = question.value.trim()
  if (!q || thinking.value) return
  messages.value.push({ role: 'user', content: q })
  question.value = ''
  thinking.value = true
  evidences.value = []
  const aiMsg = { role: 'ai', content: '', fallback: false }
  messages.value.push(aiMsg)
  try {
    await streamQuery(projectId, q, (event, data) => {
      if (event === 'stage') stage.value = data.message
      if (event === 'evidence') evidences.value = data.evidences
      if (event === 'token') aiMsg.content += data.delta
      if (event === 'done') {
        if (data.answer) aiMsg.content = data.answer
        if (data.evidences) evidences.value = data.evidences
        if (!evidences.value.length) aiMsg.fallback = true
      }
      if (event === 'error') aiMsg.content = '【错误】' + data.message
    })
  } catch (e) {
    aiMsg.content = '【请求失败】' + e.message
  }
  thinking.value = false
}

async function doUpload(opt) {
  try {
    const data = await uploadDocument(projectId, opt.file)
    alert('已上传，后台解析中：' + data.file_name)
  } catch (e) {
    alert('上传失败：' + e.message)
  }
}
</script>

<style scoped>
.chat-wrap { height: 100vh; display: flex; flex-direction: column; }
.head { display: flex; justify-content: space-between; align-items: center; }
.body { flex: 1; display: flex; overflow: hidden; }
.chat { flex: 1; overflow-y: auto; padding: 16px; }
.evidence { width: 320px; border-left: 1px solid #ebeef5; padding: 12px; overflow-y: auto; }
.msg { margin-bottom: 12px; }
.bubble { max-width: 80%; padding: 10px 14px; border-radius: 8px; white-space: pre-wrap; }
.user { background: #409eff; color: #fff; margin-left: auto; }
.ai { background: #f4f4f5; }
.dim { color: #909399; }
.ref { cursor: pointer; margin: 0 2px; }
.ev-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 8px; margin-bottom: 8px; cursor: pointer; }
.ev-card.active { border-color: #409eff; }
.thumb { width: 100%; border-radius: 4px; }
.ev-file { font-size: 13px; font-weight: 600; }
.ev-page { font-size: 12px; color: #909399; margin-top: 4px; }
.pdf { width: 100%; height: 300px; border: none; margin-top: 8px; }
.input-bar { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #ebeef5; }
.fallback { color: #e6a23c; margin-top: 8px; }
</style>
