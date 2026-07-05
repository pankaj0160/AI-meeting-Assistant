// client/src/api/client.js
//
// WHAT THIS FILE DOES:
// ────────────────────
// Single place for every API call the frontend makes.
// Every fetch() goes through the request() function at the bottom
// which handles: auth headers, JSON parsing, 401 redirect, error messages.
//
// WHY ONE FILE?
// If you had fetch('/meetings') scattered across 20 components,
// changing the URL or adding a header means editing 20 files.
// Here: change it once, affects everything.
//
// FIXES IN THIS VERSION:
// ─────────────────────
// FIX 1: Added getMeetingsList() that correctly reads the paginated response.
//   getMeetings() returns { items, has_more, next_cursor } NOT an array.
//   Summaries.jsx was calling getMeetings() and treating the result as an array,
//   which crashed silently (meetings.slice is not a function).
//
// FIX 2: Added all missing API functions:
//   - getDiarization, runDiarization (Speaker tab in MeetingDetail)
//   - getMeetingSentiment, runMeetingSentiment (Speakers/Sentiment tab)
//   - getWorkspaces, createWorkspace, getWorkspace (Workspaces page)
//   - getWorkspaceMembers, inviteMember (Workspace management)
//   - updateTask, patchTask (full task editing)
//   - getAuditLogs (Settings page)
//   - exportMyData, deleteMyAccount (GDPR settings)
//
// FIX 3: exportMeetingPDF now uses BASE correctly (was hardcoded '/api').

export function getApiBase() {
  // VITE_API_URL in .env.local overrides this.
  // Default '/api' works for production (same domain) and Vite proxy.
  return import.meta.env.VITE_API_URL || '/api'
}

const BASE = getApiBase()

// ── Token management ──────────────────────────────────────────────────────────

export function getToken() {
  return localStorage.getItem('summly_token')
}

export function setToken(token) {
  localStorage.setItem('summly_token', token)
}

export function removeToken() {
  localStorage.removeItem('summly_token')
}

// ── Core request helper ───────────────────────────────────────────────────────
//
// Every API call goes through here. This function:
//   1. Adds the Authorization: Bearer <token> header automatically
//   2. Sets Content-Type: application/json for non-file uploads
//   3. If the server returns 401 (token expired), clears the token
//      so the ProtectedRoute redirects to /login automatically
//   4. If the server returns any error, throws with the server's message
//      so catch blocks in components can show the real error to the user

async function request(path, options = {}) {
  const token   = getToken()
  const headers = { ...(options.headers || {}) }

  // Don't set Content-Type for FormData (file uploads) —
  // the browser sets it automatically with the correct boundary string
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  // 401 = expired/invalid token → clear it, ProtectedRoute handles redirect
  if (res.status === 401) {
    removeToken()
    throw new Error('Session expired. Please log in again.')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || err.error || err.message || `HTTP ${res.status}`)
  }

  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiRegister(full_name, email, password) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ full_name, email, password }),
  })
}

export async function apiLogin(email, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function apiGetMe() {
  return request('/auth/me')
}

export async function apiUpdateProfile(data) {
  return request('/auth/me', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function apiChangePassword(current_password, new_password) {
  return request('/auth/me/password', {
    method: 'PUT',
    body: JSON.stringify({ current_password, new_password }),
  })
}

export async function apiForgotPassword(email) {
  return request('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export async function apiResetPassword(token, new_password) {
  return request('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password }),
  })
}

// ── Meetings ──────────────────────────────────────────────────────────────────

// FIX: getMeetings() returns a paginated object { items, has_more, next_cursor }.
// Renamed to getMeetings for paginated usage (Dashboard, Meetings page).
// cursor = id of the last item you already have (undefined for first page).
export async function getMeetings({ cursor, limit = 20 } = {}) {
  const params = new URLSearchParams({ limit })
  if (cursor) params.set('cursor', cursor)
  return request(`/meetings?${params}`)
}

// FIX: getMeetingsList() returns ONLY the items array — easier for Summaries.jsx
// and other places that just need a flat list without pagination handling.
// Uses limit=100 to fetch all recent meetings in one call.
export async function getMeetingsList(limit = 50) {
  const data = await getMeetings({ limit })
  // data is { items: [...], has_more: bool, next_cursor: int|null }
  return Array.isArray(data) ? data : (data.items || [])
}

export async function getMeeting(id) {
  return request(`/meetings/${id}`)
}

// FIX: there was previously no way to delete a meeting anywhere in the
// app — the only option was deleting it directly in Supabase, which never
// cleaned up its ChromaDB vectors and could cause deleted meetings' content
// to leak into future chat (see vacuumOrphanedChunks() below for cleaning
// up damage already done that way).
export async function deleteMeeting(id) {
  return request(`/meetings/${id}`, { method: 'DELETE' })
}

export async function getMeetingIntelligence(id) {
  return request(`/meetings/${id}/intelligence`)
}

export async function getMeetingTasks(id) {
  return request(`/meetings/${id}/tasks`)
}

// ── Tasks / Action Items ──────────────────────────────────────────────────────

export async function getTasks({ cursor, limit = 20, status, priority, owner } = {}) {
  const params = new URLSearchParams({ limit })
  if (cursor)   params.set('cursor',   cursor)
  if (status)   params.set('status',   status)
  if (priority) params.set('priority', priority)
  if (owner)    params.set('owner',    owner)
  return request(`/tasks?${params}`)
}

export async function getTaskStats() {
  return request('/tasks/stats')
}

export async function updateTaskStatus(itemId, status) {
  return request(`/tasks/${itemId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

// FIX: patchTask — update any field (owner, deadline, priority, status)
export async function patchTask(itemId, fields) {
  return request(`/tasks/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  })
}

export async function deleteTask(itemId) {
  return request(`/tasks/${itemId}`, { method: 'DELETE' })
}

// ── Upload ────────────────────────────────────────────────────────────────────

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/upload', { method: 'POST', body: form })
}

// Async upload (Celery background) — returns job_id immediately
export async function uploadFileAsync(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/upload/async', { method: 'POST', body: form })
}

export async function getJobStatus(jobId) {
  return request(`/jobs/${jobId}/status`)
}

// ── YouTube ───────────────────────────────────────────────────────────────────

export async function processYouTube(url) {
  return request('/youtube', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function chatWithMeeting(query, meetingId) {
  return request('/chat/meeting', {
    method: 'POST',
    body: JSON.stringify({ query, meeting_id: meetingId }),
  })
}

export async function chatAcrossMeetings(query) {
  return request('/chat/search', {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

// ── Stats & Analytics ─────────────────────────────────────────────────────────

export async function getStats() {
  return request('/stats')
}

export async function getAnalytics() {
  return request('/analytics')
}

// ── Health check ──────────────────────────────────────────────────────────────

export async function getHealth() {
  return request('/health')
}

// ── RAG Reindex ───────────────────────────────────────────────────────────────

export async function reindexAll() {
  return request('/rag/reindex', { method: 'POST' })
}

export async function getReindexStatus(jobId) {
  return request(`/rag/reindex/status?job_id=${jobId}`)
}

// FIX: one-off cleanup for meetings that were deleted directly in Supabase
// before the DELETE /meetings/{id} endpoint existed — their ChromaDB
// vectors were never removed and could surface in chat (including under a
// different, newer meeting that happened to reuse the same id). This
// removes any ChromaDB content whose meeting_id no longer exists anywhere
// in Postgres. Safe to run any time; it's a no-op once caught up.
export async function vacuumOrphanedChunks() {
  return request('/rag/vacuum-orphaned', { method: 'POST' })
}

// ── Contact ───────────────────────────────────────────────────────────────────

export async function sendContactForm(name, email, subject, message) {
  return request('/contact', {
    method: 'POST',
    body: JSON.stringify({ name, email, subject, message }),
  })
}

// ── Advanced Intelligence ─────────────────────────────────────────────────────

export async function getMeetingHealth(id) {
  return request(`/meetings/${id}/health`)
}

export async function getMeetingQuotes(id) {
  return request(`/meetings/${id}/quotes`)
}

export async function getMeetingAITitle(id) {
  return request(`/meetings/${id}/title`)
}

export async function getMeetingAgenda(id) {
  return request(`/meetings/${id}/agenda`)
}

// ── Export ────────────────────────────────────────────────────────────────────

// FIX: was hardcoded '/api/meetings/...' — now uses BASE from getApiBase()
export async function exportMeetingPDF(id) {
  const token = getToken()
  const res   = await fetch(`${BASE}/meetings/${id}/export/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('PDF export failed')
  return res.blob()
}

export async function getFollowupEmail(id) {
  return request(`/meetings/${id}/followup-email`)
}

// ── Diarization (Speaker Detection) ──────────────────────────────────────────
//
// Diarization = identifying WHO spoke WHEN in a recording.
// The backend uses pyannote.audio to label each segment with a speaker ID.
//
// Flow:
//   1. POST /meetings/{id}/diarize  → runs pyannote, stores result
//   2. GET  /meetings/{id}/diarization → reads stored result
//
// The POST is slow (pyannote is a heavy model). The GET is instant.
// MeetingDetail calls GET first — if result exists, shows it.
// If not, shows a "Run Analysis" button that calls POST.

export async function runDiarization(id) {
  return request(`/meetings/${id}/diarize`, { method: 'POST' })
}

export async function getDiarization(id) {
  return request(`/meetings/${id}/diarization`)
}

// ── Sentiment Analysis ────────────────────────────────────────────────────────
//
// POST runs the LLM-based sentiment analysis (requires diarization first).
// GET returns stored results instantly.

export async function runSentimentAnalysis(id) {
  return request(`/meetings/${id}/sentiment`, { method: 'POST' })
}

export async function getMeetingSentiment(id) {
  return request(`/meetings/${id}/sentiment`)
}

// ── Workspaces ────────────────────────────────────────────────────────────────

export async function getWorkspaces() {
  return request('/workspaces')
}

export async function createWorkspace(name, description = '', type = 'individual', color = '#10b981') {
  return request('/workspaces', {
    method: 'POST',
    body: JSON.stringify({ name, description, type, color }),
  })
}

export async function getWorkspace(id) {
  return request(`/workspaces/${id}`)
}

export async function updateWorkspace(id, fields) {
  return request(`/workspaces/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  })
}

export async function deleteWorkspace(id) {
  return request(`/workspaces/${id}`, { method: 'DELETE' })
}

export async function getWorkspaceMeetings(workspaceId) {
  return request(`/workspaces/${workspaceId}/meetings`)
}

export async function addMeetingToWorkspace(workspaceId, meetingId) {
  return request(`/workspaces/${workspaceId}/meetings/${meetingId}`, { method: 'POST' })
}

export async function removeMeetingFromWorkspace(workspaceId, meetingId) {
  return request(`/workspaces/${workspaceId}/meetings/${meetingId}`, { method: 'DELETE' })
}

// FIX: previously there was no way to ask "which workspace is this meeting in?" —
// backend had the DB helper (get_workspace_for_meeting) but never exposed it.
// Used by MeetingDetail to show/manage a meeting's workspace assignment.
export async function getMeetingWorkspace(meetingId) {
  return request(`/meetings/${meetingId}/workspace`)
}

export async function getWorkspaceMembers(workspaceId) {
  return request(`/workspaces/${workspaceId}/members`)
}

export async function inviteMember(workspaceId, email, role = 'member') {
  return request(`/workspaces/${workspaceId}/members`, {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  })
}

export async function removeMember(workspaceId, userId) {
  return request(`/workspaces/${workspaceId}/members/${userId}`, { method: 'DELETE' })
}

export async function getWorkspaceIntelligence(workspaceId) {
  return request(`/workspaces/${workspaceId}/intelligence`)
}

export async function getWorkspaceTasks(workspaceId, status) {
  const params = status ? `?status=${status}` : ''
  return request(`/workspaces/${workspaceId}/tasks${params}`)
}

export async function chatWithWorkspace(workspaceId, query) {
  return request(`/workspaces/${workspaceId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ query }),
  })
}

// ── Webhooks ──────────────────────────────────────────────────────────────────

export async function getWebhooks() {
  return request('/webhooks')
}

export async function createWebhook(url, events) {
  return request('/webhooks', {
    method: 'POST',
    body: JSON.stringify({ url, events }),
  })
}

export async function deleteWebhook(id) {
  return request(`/webhooks/${id}`, { method: 'DELETE' })
}

export async function getWebhookEvents(webhookId, limit = 50) {
  return request(`/webhooks/${webhookId}/events?limit=${limit}`)
}

// ── Audit Logs ────────────────────────────────────────────────────────────────

export async function getAuditLogs({ resource_type, resource_id, limit = 100 } = {}) {
  const params = new URLSearchParams({ limit })
  if (resource_type) params.set('resource_type', resource_type)
  if (resource_id)   params.set('resource_id',   resource_id)
  return request(`/audit-logs?${params}`)
}

// ── GDPR ──────────────────────────────────────────────────────────────────────

export async function exportMyData() {
  const token = getToken()
  const res   = await fetch(`${BASE}/me/export`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Export failed')
  return res.blob()   // returns a downloadable JSON file
}

export async function deleteMyAccount(confirmText) {
  return request('/me/account', {
    method: 'DELETE',
    body: JSON.stringify({ confirm: confirmText }),
  })
}