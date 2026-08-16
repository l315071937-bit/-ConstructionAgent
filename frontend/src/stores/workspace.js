import { defineStore } from 'pinia'

function readJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key) || '')
  } catch (e) {
    return fallback
  }
}

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    recentProjectIds: readJson('ca_recent_projects', []),
    conversationIds: readJson('ca_project_conversations', {}),
    compactMode: readJson('ca_compact_mode', false),
    topK: readJson('ca_top_k', 8)
  }),
  actions: {
    rememberProject(projectId) {
      const id = Number(projectId)
      this.recentProjectIds = [id, ...this.recentProjectIds.filter(item => item !== id)].slice(0, 6)
      localStorage.setItem('ca_recent_projects', JSON.stringify(this.recentProjectIds))
    },
    conversationKey(projectId, agentType = 'project') {
      return agentType === 'project'
        ? String(projectId) : String(projectId) + ':' + agentType
    },
    getConversation(projectId, agentType = 'project') {
      return this.conversationIds[this.conversationKey(projectId, agentType)] || ''
    },
    setCompactMode(value) {
      this.compactMode = value
      localStorage.setItem('ca_compact_mode', JSON.stringify(value))
    },
    setTopK(value) {
      this.topK = value
      localStorage.setItem('ca_top_k', JSON.stringify(value))
    },
    setConversation(projectId, conversationId, agentType = 'project') {
      this.conversationIds = {
        ...this.conversationIds,
        [this.conversationKey(projectId, agentType)]: conversationId
      }
      localStorage.setItem('ca_project_conversations', JSON.stringify(this.conversationIds))
    },
    clearConversation(projectId, agentType = 'project') {
      const next = { ...this.conversationIds }
      delete next[this.conversationKey(projectId, agentType)]
      this.conversationIds = next
      localStorage.setItem('ca_project_conversations', JSON.stringify(next))
    }
  }
})
