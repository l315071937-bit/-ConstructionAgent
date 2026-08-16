// fetch 封装 + POST SSE 流解析（EventSource 仅支持 GET，故用 fetch 流）
import { useAuthStore } from '../stores/auth'

const BASE = '/api/v1'

function apiUrl(path) {
  return path.startsWith(BASE + '/') ? path : BASE + path
}

function handleUnauthorized(resp, auth) {
  if (resp.status === 401) {
    auth.logout()
    window.location = '/login'
  }
}

async function request(method, path, body) {
  const auth = useAuthStore()
  const resp = await fetch(apiUrl(path), {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(auth.token ? { Authorization: 'Bearer ' + auth.token } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    handleUnauthorized(resp, auth)
    throw new Error((data.error && data.error.message) || ('HTTP ' + resp.status))
  }
  return data
}

export async function uploadDocument(projectId, file, folderId = '') {
  const auth = useAuthStore()
  const form = new FormData()
  form.append('file', file)
  const folderQuery = folderId ? '?folder_id=' + encodeURIComponent(folderId) : ''
  const resp = await fetch(BASE + '/projects/' + projectId + '/documents' + folderQuery, {
    method: 'POST',
    headers: auth.token ? { Authorization: 'Bearer ' + auth.token } : {},
    body: form
  })
  const data = await resp.json().catch(() => ({}))
  if (!resp.ok) throw new Error((data.error && data.error.message) || ('HTTP ' + resp.status))
  return data
}

export async function fetchProtectedBlobUrl(path) {
  const auth = useAuthStore()
  const resp = await fetch(apiUrl(path), {
    headers: auth.token ? { Authorization: 'Bearer ' + auth.token } : {}
  })
  if (!resp.ok) {
    handleUnauthorized(resp, auth)
    const data = await resp.json().catch(() => ({}))
    throw new Error((data.error && data.error.message) || ('HTTP ' + resp.status))
  }
  return URL.createObjectURL(await resp.blob())
}

// SSE 流式问答：onEvent(event, data) 回调
export async function streamQuery(projectId, question, onEvent, topK = 8, conversationId = null) {
  const auth = useAuthStore()
  const resp = await fetch(BASE + '/projects/' + projectId + '/retrieval/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: 'Bearer ' + auth.token
    },
    body: JSON.stringify({ question, top_k: topK, conversation_id: conversationId })
  })
  if (!resp.ok || !resp.body) {
    const data = await resp.json().catch(() => ({}))
    throw new Error((data.error && data.error.message) || ('HTTP ' + resp.status))
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const NL = String.fromCharCode(10)
    let idx
    while ((idx = buffer.indexOf('event:')) >= 0) {
      const end = buffer.indexOf(NL + NL, idx)
      if (end < 0) break
      const block = buffer.slice(idx, end)
      buffer = buffer.slice(end + 2)
      const evMatch = block.match(/^event: (.+)$/m)
      const dataMatch = block.match(/^data: (.+)$/m)
      if (evMatch && dataMatch) {
        let data = {}
        try { data = JSON.parse(dataMatch[1]) } catch (e) { /* 忽略 */ }
        onEvent(evMatch[1].trim(), data)
      }
    }
  }
}

export { request }
