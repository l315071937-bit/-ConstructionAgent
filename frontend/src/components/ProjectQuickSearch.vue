<template>
  <el-autocomplete
    v-model="keyword"
    class="project-quick-search"
    :debounce="250"
    :fetch-suggestions="fetchSuggestions"
    :placeholder="placeholder"
    :trigger-on-focus="false"
    clearable
    value-key="name"
    @select="selectProject"
  >
    <template #prefix><el-icon><Search /></el-icon></template>
    <template #default="{ item }">
      <div class="suggestion">
        <span class="suggestion-icon"><el-icon><Folder /></el-icon></span>
        <span class="suggestion-copy">
          <strong>{{ item.name }}</strong>
          <small>{{ item.description || '可访问项目' }}</small>
        </span>
        <span class="suggestion-count">{{ item.document_count || 0 }} 份资料</span>
      </div>
    </template>
  </el-autocomplete>
</template>

<script setup>
import { Folder, Search } from '@element-plus/icons-vue'
import { request } from '../api/client'

defineProps({
  placeholder: { type: String, default: '输入项目名称或地区关键词' }
})
const emit = defineEmits(['select'])
const keyword = defineModel({ type: String, default: '' })
let requestVersion = 0

async function fetchSuggestions(value, callback) {
  const query = value.trim()
  const version = ++requestVersion
  if (query.length < 2) {
    callback([])
    return
  }
  try {
    const data = await request(
      'GET', '/projects/suggestions?q=' + encodeURIComponent(query) + '&limit=3')
    if (version === requestVersion) callback(data.items)
  } catch (error) {
    if (version === requestVersion) callback([])
  }
}

function selectProject(project) {
  keyword.value = project.name
  emit('select', project)
}
</script>

<style scoped>
.project-quick-search { width: 100%; }
.suggestion { width: min(460px, calc(100vw - 40px)); display: flex; align-items: center; gap: 10px; padding: 5px 0; }
.suggestion-icon { width: 30px; height: 30px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 5px; background: #edf3fb; color: #1f5fbf; }
.suggestion-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; line-height: 1.4; }
.suggestion-copy strong, .suggestion-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.suggestion-copy strong { color: #263445; font-size: 13px; }
.suggestion-copy small, .suggestion-count { color: #7a8594; font-size: 11px; }
.suggestion-count { flex: 0 0 auto; }
</style>
