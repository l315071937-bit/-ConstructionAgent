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
    evidenceVisible: readJson('ca_evidence_visible', true),
    compactMode: readJson('ca_compact_mode', false),
    topK: readJson('ca_top_k', 8)
  }),
  actions: {
    rememberProject(projectId) {
      const id = Number(projectId)
      this.recentProjectIds = [id, ...this.recentProjectIds.filter(item => item !== id)].slice(0, 6)
      localStorage.setItem('ca_recent_projects', JSON.stringify(this.recentProjectIds))
    },
    setEvidenceVisible(value) {
      this.evidenceVisible = value
      localStorage.setItem('ca_evidence_visible', JSON.stringify(value))
    },
    setCompactMode(value) {
      this.compactMode = value
      localStorage.setItem('ca_compact_mode', JSON.stringify(value))
    },
    setTopK(value) {
      this.topK = value
      localStorage.setItem('ca_top_k', JSON.stringify(value))
    }
  }
})
