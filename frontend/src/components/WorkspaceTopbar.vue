<template>
  <header class="topbar">
    <div class="brand-group">
      <button class="icon-button mobile-nav" type="button" title="打开导航" @click="$emit('open-navigation')">
        <el-icon><Menu /></el-icon>
      </button>
      <button class="brand" type="button" @click="$emit('projects')">
        <span class="brand-mark">CA</span>
        <span class="brand-name">ConstructionAgent</span>
      </button>
    </div>

    <button v-if="project" class="project-lock" type="button" @click="$emit('switch-project')">
      <el-icon><Lock /></el-icon>
      <span class="project-lock-label">当前知识库</span>
      <strong>{{ project.name }}</strong>
      <el-icon><ArrowDown /></el-icon>
    </button>

    <div class="top-actions">
      <button class="icon-button evidence-toggle" type="button" title="打开检索依据" @click="$emit('open-evidence')">
        <el-icon><Files /></el-icon>
        <span v-if="evidenceCount" class="counter">{{ evidenceCount }}</span>
      </button>
      <button class="icon-button" type="button" title="设置" @click="$emit('settings')">
        <el-icon><Setting /></el-icon>
      </button>
      <el-dropdown trigger="click" @command="handleCommand">
        <button class="user-menu" type="button">
          <el-avatar :size="32">{{ userInitial }}</el-avatar>
          <span class="user-name">{{ user && user.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="projects">切换项目</el-dropdown-item>
            <el-dropdown-item command="settings">工作台设置</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown, Files, Lock, Menu, Setting } from '@element-plus/icons-vue'

const props = defineProps({
  user: { type: Object, default: null },
  project: { type: Object, default: null },
  evidenceCount: { type: Number, default: 0 }
})

const emit = defineEmits(['logout', 'open-evidence', 'open-navigation', 'projects', 'settings', 'switch-project'])
const userInitial = computed(() => (props.user && props.user.username ? props.user.username.slice(0, 1).toUpperCase() : 'U'))

function handleCommand(command) {
  emit(command)
}
</script>

<style scoped>
.topbar { height: 56px; display: grid; grid-template-columns: minmax(240px, 1fr) auto minmax(240px, 1fr); align-items: center; padding: 0 18px; border-bottom: 1px solid #dfe3e8; background: #fff; color: #17202a; }
.brand-group, .top-actions { display: flex; align-items: center; gap: 8px; }
.top-actions { justify-content: flex-end; }
.brand { display: flex; align-items: center; gap: 10px; padding: 0; border: 0; background: transparent; cursor: pointer; color: inherit; }
.brand-mark { width: 32px; height: 32px; display: grid; place-items: center; border-radius: 6px; background: #2166d1; color: #fff; font-size: 12px; font-weight: 700; }
.brand-name { font-size: 16px; font-weight: 700; }
.project-lock { min-width: 0; max-width: 440px; height: 34px; display: flex; align-items: center; gap: 7px; padding: 0 10px; border: 1px solid #d9e2ef; border-radius: 6px; background: #f7f9fc; color: #334155; cursor: pointer; }
.project-lock-label { color: #718096; font-size: 12px; }
.project-lock strong { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.icon-button { position: relative; width: 34px; height: 34px; display: grid; place-items: center; border: 1px solid transparent; border-radius: 5px; background: transparent; color: #52606d; cursor: pointer; font-size: 18px; }
.icon-button:hover { background: #f0f3f7; color: #1f5fbf; }
.counter { position: absolute; top: -3px; right: -3px; min-width: 16px; height: 16px; padding: 0 3px; border-radius: 8px; background: #d94841; color: #fff; font-size: 10px; line-height: 16px; }
.user-menu { display: flex; align-items: center; gap: 7px; height: 38px; padding: 0 4px 0 2px; border: 0; background: transparent; color: #334155; cursor: pointer; }
.user-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.mobile-nav { display: none; }
@media (max-width: 1040px) {
  .topbar { grid-template-columns: 1fr auto 1fr; padding: 0 12px; }
  .brand-name, .project-lock-label { display: none; }
  .project-lock { max-width: 300px; }
}
@media (max-width: 760px) {
  .topbar { grid-template-columns: 1fr auto; }
  .mobile-nav { display: grid; }
  .project-lock { display: none; }
  .user-name { display: none; }
}
</style>
