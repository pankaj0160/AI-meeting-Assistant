// client/src/context/WorkspaceContext.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// Before this file existed, the Workspaces page was an island: it could list,
// create, and delete workspaces, but nothing else in the app knew or cared
// which workspace (if any) you'd picked. The sidebar showed the same global
// stats no matter what. Meetings always showed every meeting you own.
//
// This context is the missing piece of shared state: "which workspace is
// currently active?" Anything in the app — Sidebar, Meetings, Dashboard,
// future features — can read `activeWorkspaceId` from here and filter/scope
// itself accordingly, instead of each page re-inventing its own notion of
// "current workspace."
//
// Persistence: the chosen workspace id is saved to localStorage so it
// survives a page refresh. On login we re-validate it still exists (in case
// the workspace was deleted, or this is a different account on the same
// browser) and clear it silently if not.

import {
  createContext, useContext, useState, useEffect, useCallback, useMemo,
} from 'react'
import { getWorkspaces, getWorkspaceIntelligence } from '../api/client'
import { useAuth } from './AuthContext'

const STORAGE_KEY = 'summly_active_workspace_id'
const WorkspaceContext = createContext(null)

export function WorkspaceProvider({ children }) {
  const { isAuthenticated } = useAuth()

  const [workspaces,        setWorkspaces]        = useState([])
  const [activeWorkspaceId, setActiveWorkspaceId]  = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? Number(saved) : null
  })
  const [workspaceStats, setWorkspaceStats] = useState(null) // intelligence summary for the active workspace
  const [loading,        setLoading]        = useState(true)
  const [statsLoading,   setStatsLoading]   = useState(false)

  // ── Load the workspace list whenever the user logs in ──────────────────────
  const refreshWorkspaces = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getWorkspaces()
      const list = Array.isArray(data) ? data : (data.workspaces || [])
      setWorkspaces(list)
      return list
    } catch {
      setWorkspaces([])
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      // Logged out — reset everything so a different user on the same
      // browser doesn't briefly see the previous account's workspace.
      setWorkspaces([])
      setWorkspaceStats(null)
      setLoading(false)
      return
    }

    let cancelled = false
    refreshWorkspaces().then(list => {
      if (cancelled) return
      // Re-validate the saved workspace id still exists for this user.
      setActiveWorkspaceId(prev => {
        if (prev == null) return null
        const stillExists = list.some(w => w.id === prev)
        if (!stillExists) {
          localStorage.removeItem(STORAGE_KEY)
          return null
        }
        return prev
      })
    })
    return () => { cancelled = true }
  }, [isAuthenticated, refreshWorkspaces])

  // ── Fetch aggregate stats whenever the active workspace changes ────────────
  useEffect(() => {
    if (activeWorkspaceId == null) {
      setWorkspaceStats(null)
      return
    }
    let cancelled = false
    setStatsLoading(true)
    getWorkspaceIntelligence(activeWorkspaceId)
      .then(data => { if (!cancelled) setWorkspaceStats(data) })
      .catch(() => { if (!cancelled) setWorkspaceStats(null) })
      .finally(() => { if (!cancelled) setStatsLoading(false) })
    return () => { cancelled = true }
  }, [activeWorkspaceId])

  const selectWorkspace = useCallback((id) => {
    setActiveWorkspaceId(id)
    if (id == null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, String(id))
    }
  }, [])

  const activeWorkspace = useMemo(
    () => workspaces.find(w => w.id === activeWorkspaceId) || null,
    [workspaces, activeWorkspaceId],
  )

  // Called by the Workspaces page after create/delete so the sidebar/switcher
  // stay in sync without waiting for a full refetch.
  const upsertWorkspace = useCallback((ws) => {
    setWorkspaces(prev => {
      const exists = prev.some(w => w.id === ws.id)
      return exists ? prev.map(w => (w.id === ws.id ? { ...w, ...ws } : w)) : [ws, ...prev]
    })
  }, [])

  const removeWorkspaceLocal = useCallback((id) => {
    setWorkspaces(prev => prev.filter(w => w.id !== id))
    setActiveWorkspaceId(prev => {
      if (prev !== id) return prev
      localStorage.removeItem(STORAGE_KEY)
      return null
    })
  }, [])

  return (
    <WorkspaceContext.Provider value={{
      workspaces,
      loading,
      activeWorkspaceId,
      activeWorkspace,
      workspaceStats,
      statsLoading,
      selectWorkspace,
      refreshWorkspaces,
      upsertWorkspace,
      removeWorkspaceLocal,
    }}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export const useWorkspace = () => useContext(WorkspaceContext)