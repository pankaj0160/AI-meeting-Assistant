// client/src/api/client.js

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Meetings ─────────────────────────────────────────────────────────────────

export async function getMeetings() {
  return request('/meetings')
}

export async function getMeeting(id) {
  return request(`/meetings/${id}`)
}

export async function getMeetingIntelligence(id) {
  return request(`/meetings/${id}/intelligence`)
}

// ── Upload ────────────────────────────────────────────────────────────────────

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/upload', { method: 'POST', body: form })
}

// ── YouTube ───────────────────────────────────────────────────────────────────

export async function processYouTube(url) {
  return request('/youtube', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ url }),
  })
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function chatWithMeeting(query, meetingId) {
  return request('/chat/meeting', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ query, meeting_id: meetingId }),
  })
}

export async function chatAcrossMeetings(query) {
  return request('/chat/search', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ query }),
  })
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth() {
  return request('/health')
}


// ── Stats ─────────────────────────────────────────────────────────────────────

export async function getStats() {
  return request('/stats')
}

// ── Reindex ───────────────────────────────────────────────────────────────────

export async function reindexAll() {
  return request('/rag/reindex', { method: 'POST' })
}