<template>
  <aside class="sidebar">
    <el-button class="new-chat" type="primary" plain @click="$emit('new-chat')">
      <el-icon><Plus /></el-icon>
      新建对话
    </el-button>

    <section class="nav-section">
      <div class="section-label">Agent</div>
      <button class="nav-item" :class="{ active: activeAgent === 'project' }" type="button"
              @click="$emit('select-agent', 'project')">
        <el-icon><Search /></el-icon>
        <span>项目资料检索</span>
        <span class="status-dot"></span>
      </button>
      <button class="nav-item" :class="{ active: activeAgent === 'standard' }" type="button"
              @click="$emit('select-agent', 'standard')">
        <el-icon><Reading /></el-icon>
        <span>规范查询</span>
        <span class="status-dot"></span>
      </button>
      <el-tooltip content="施工方案 Agent 尚未开放" placement="right">
        <button class="nav-item disabled" type="button" disabled>
          <el-icon><EditPen /></el-icon>
          <span>施工方案编制</span>
        </button>
      </el-tooltip>
    </section>

    <section class="nav-section project-section">
      <div class="section-heading">
        <span class="section-label">项目知识库</span>
        <el-button link type="primary" @click="$emit('switch-project')">切换</el-button>
      </div>
      <button v-if="currentProject" class="locked-project" type="button" @click="$emit('switch-project')">
        <span class="project-icon"><el-icon><Lock /></el-icon></span>
        <span class="project-copy">
          <strong>{{ currentProject.name }}</strong>
          <small>{{ currentProject.document_count || 0 }} 份资料</small>
        </span>
      </button>
      <el-input v-model="projectFilter" class="project-search" size="small" clearable placeholder="搜索项目名称">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div class="project-list">
        <button v-for="project in filteredProjects" :key="project.project_id" class="project-link"
                :class="{ current: currentProject && project.project_id === currentProject.project_id }"
                type="button" @click="$emit('select-project', project)">
          <el-icon><Folder /></el-icon>
          <span>{{ project.name }}</span>
        </button>
      </div>
    </section>

    <section class="nav-section conversation-section">
      <div class="section-label">当前会话</div>
      <div class="conversation-item" :class="{ empty: !sessionTitle }">
        <el-icon><ChatDotRound /></el-icon>
        <span>{{ sessionTitle || '尚未开始对话' }}</span>
      </div>
    </section>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ChatDotRound, EditPen, Folder, Lock, Plus, Reading, Search } from '@element-plus/icons-vue'

const props = defineProps({
  activeAgent: { type: String, default: 'project' },
  currentProject: { type: Object, default: null },
  projects: { type: Array, default: () => [] },
  sessionTitle: { type: String, default: '' }
})

defineEmits(['new-chat', 'select-agent', 'select-project', 'switch-project'])
const projectFilter = ref('')
const filteredProjects = computed(() => {
  const keyword = projectFilter.value.trim().toLowerCase()
  return props.projects
    .filter(project => !keyword || project.name.toLowerCase().includes(keyword))
    .slice(0, 6)
})
</script>

<style scoped>
.sidebar { height: 100%; display: flex; flex-direction: column; gap: 18px; padding: 16px 14px; border-right: 1px solid #dfe3e8; background: #f7f8fa; overflow: hidden; }
.new-chat { width: 100%; height: 36px; justify-content: flex-start; }
.nav-section { display: flex; flex-direction: column; gap: 5px; }
.section-label { color: #7a8594; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.section-heading { display: flex; align-items: center; justify-content: space-between; }
.nav-item { width: 100%; height: 36px; display: flex; align-items: center; gap: 10px; padding: 0 10px; border: 0; border-radius: 5px; background: transparent; color: #344054; cursor: pointer; font-size: 13px; text-align: left; }
.nav-item.active { background: #e8eef8; color: #174ea6; font-weight: 600; }
.nav-item.disabled { color: #98a2b3; cursor: not-allowed; }
.status-dot { width: 7px; height: 7px; margin-left: auto; border-radius: 50%; background: #25855a; }
.project-section { min-height: 0; }
.locked-project { display: flex; align-items: center; gap: 9px; padding: 10px; border: 1px solid #cbd7e8; border-radius: 6px; background: #fff; color: #263445; cursor: pointer; text-align: left; }
.project-icon { width: 28px; height: 28px; flex: 0 0 auto; display: grid; place-items: center; border-radius: 5px; background: #edf4ff; color: #1f5fbf; }
.project-copy { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.project-copy strong, .project-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-copy strong { font-size: 13px; }
.project-copy small { color: #7a8594; font-size: 11px; }
.project-search { margin-top: 4px; }
.project-list { min-height: 0; max-height: 168px; overflow-y: auto; }
.project-link { width: 100%; height: 32px; display: flex; align-items: center; gap: 8px; padding: 0 9px; border: 0; border-radius: 4px; background: transparent; color: #52606d; cursor: pointer; font-size: 12px; text-align: left; }
.project-link span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-link:hover { background: #edf0f4; }
.project-link.current { color: #1f5fbf; font-weight: 600; }
.conversation-section { margin-top: auto; border-top: 1px solid #dfe3e8; padding-top: 14px; }
.conversation-item { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 8px; color: #344054; font-size: 12px; }
.conversation-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conversation-item.empty { color: #98a2b3; }
</style>
