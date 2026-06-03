// client/src/api/client.js

const BASE = '/api'

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