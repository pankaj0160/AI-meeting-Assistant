// client/src/api/client.js

// FIX: Single source of truth for the API base URL.
//
// Before this fix, Upload.jsx had its own copy:
//   const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
//
// That hardcoded 'http://localhost:8000' fallback pointed to the developer's
// own machine. In production, users were calling localhost — their own computer
// — which has no server running. File uploads silently failed.
//
// Fix: export getApiBase() from here so every file uses the same value.
// The fallback '/api' is a relative URL — it works on any domain automatically.
//
// HOW TO CONFIGURE:
//   Development (default): VITE_API_URL not set → uses '/api'
//   If your dev backend runs on a different port, set in .env.local:
//     VITE_API_URL=http://localhost:8000
//   Production: leave VITE_API_URL unset → '/api' resolves to your domain.

export function getApiBase() {
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

// ── Core request ──────────────────────────────────────────────────────────────

async function request(path, options = {}) {
  const token = getToken()

  const headers = {
    ...(options.headers || {}),
  }

  // Only set Content-Type for non-FormData requests
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  // Attach token if present
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  })

  // Handle 401 globally — clear token
  // Do NOT redirect here — AuthContext handles the redirect via ProtectedRoute
  if (res.status === 401) {
    removeToken()
    throw new Error('Session expired. Please log in again.')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || err.error || `HTTP ${res.status}`)
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

// FIX: getMeetings now accepts pagination params.
// cursor = id of the last meeting you already have (undefined for first page)
// limit  = how many to load per page (default 20)
export async function getMeetings({ cursor, limit = 20 } = {}) {
  const params = new URLSearchParams({ limit })
  if (cursor) params.set('cursor', cursor)
  return request(`/meetings?${params}`)
}

// FIX: getTasks now accepts pagination and filter params.
export async function getTasks({ cursor, limit = 20, status, priority, owner } = {}) {
  const params = new URLSearchParams({ limit })
  if (cursor)   params.set('cursor',   cursor)
  if (status)   params.set('status',   status)
  if (priority) params.set('priority', priority)
  if (owner)    params.set('owner',    owner)
  return request(`/tasks?${params}`)
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

// ── Stats ─────────────────────────────────────────────────────────────────────

export async function getStats() {
  return request('/stats')
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function getHealth() {
  return request('/health')
}

// ── Reindex ───────────────────────────────────────────────────────────────────

export async function reindexAll() {
  return request('/rag/reindex', { method: 'POST' })
}


// ── Contact ───────────────────────────────────────────────────────────────────

export async function sendContactForm(name, email, subject, message) {
  return request('/contact', {
    method: 'POST',
    body: JSON.stringify({ name, email, subject, message }),
  })
}

// ── Phase 6 — Advanced Intelligence ───────────────────────────────────────────

export async function getMeetingHealth(id) {
  return request(`/meetings/${id}/health`)
}

export async function getMeetingQuotes(id) {
  return request(`/meetings/${id}/quotes`)
}

export async function getMeetingAITitle(id) {
  return request(`/meetings/${id}/title`)
}

export async function updateTaskStatus(itemId, status) {
  return request(`/tasks/${itemId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status }),
  })
}

// ── Phase 7 — Export ──────────────────────────────────────────────────────────

export async function exportMeetingPDF(id) {
  const token = getToken()
  const res = await fetch(`/api/meetings/${id}/export/pdf`, {
    headers: { 'Authorization': `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('PDF export failed')
  return res.blob()
}

export async function getFollowupEmail(id) {
  return request(`/meetings/${id}/followup-email`)
}