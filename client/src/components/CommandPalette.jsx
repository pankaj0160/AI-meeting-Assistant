// components/CommandPalette.jsx
// Press Cmd+K (Mac) or Ctrl+K (Windows) from anywhere to open.
//
// HOW IT WORKS:
//   1. Global keydown listener (useEffect in main.jsx) catches Cmd+K
//   2. Sets isOpen=true in CommandPaletteProvider context
//   3. This component renders a modal overlay with a search input
//   4. Arrow keys navigate, Enter runs the selected action
//   5. Escape closes — also clicking outside closes
//
// WHY A PORTAL?
//   The modal needs to appear on top of everything regardless of where
//   in the DOM it lives. ReactDOM.createPortal() renders it directly
//   into document.body — outside the normal component tree — so z-index
//   and stacking contexts never cause issues.

import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../ThemeContext'
import { getMeetings } from '../api/client'
import { Kbd } from './ui'

const CPContext = createContext(null)

// ── Pages and actions (static) ────────────────────────────────────────────────
const PAGES = [
  { id: 'dashboard', label: 'Go to Dashboard',  icon: '🏠', to: '/app',           group: 'Navigate' },
  { id: 'upload',    label: 'Upload a Meeting',  icon: '⬆️', to: '/app/upload',    group: 'Navigate' },
  { id: 'meetings',  label: 'View All Meetings', icon: '🎙️', to: '/app/meetings',  group: 'Navigate' },
  { id: 'tasks',     label: 'View Tasks',        icon: '✅', to: '/app/tasks',     group: 'Navigate' },
  { id: 'chat',      label: 'Open AI Chat',      icon: '💬', to: '/app/chat',      group: 'Navigate' },
  { id: 'analytics', label: 'Analytics',         icon: '📊', to: '/app/analytics', group: 'Navigate' },
  { id: 'settings',  label: 'Settings',          icon: '⚙️', to: '/app/settings',  group: 'Navigate' },
]

// ── Provider ──────────────────────────────────────────────────────────────────
export function CommandPaletteProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)

  // Global Cmd+K / Ctrl+K listener
  // useEffect with [] runs once on mount — attaches to window
  // The cleanup function (return) removes the listener on unmount
  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()   // prevents browser default (focus URL bar in Chrome)
        setIsOpen(prev => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <CPContext.Provider value={{ isOpen, setIsOpen }}>
      {children}
      <CommandPaletteModal />
    </CPContext.Provider>
  )
}

export function useCommandPalette() {
  return useContext(CPContext)
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function CommandPaletteModal() {
  const { isOpen, setIsOpen } = useContext(CPContext)
  const { T, isDark }         = useTheme()
  const navigate              = useNavigate()

  const [query,     setQuery]     = useState('')
  const [meetings,  setMeetings]  = useState([])
  const [selected,  setSelected]  = useState(0)
  const [loading,   setLoading]   = useState(false)

  const inputRef = useRef(null)

  // Load meetings for search when palette opens
  useEffect(() => {
    if (!isOpen) { setQuery(''); setSelected(0); return }
    // Focus input immediately when modal opens
    setTimeout(() => inputRef.current?.focus(), 50)

    // Load meetings in background for searching
    setLoading(true)
    getMeetings({ limit: 50 })
      .then(d => setMeetings(d.items || []))
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false))
  }, [isOpen])

  // Build filtered results from query
  const results = buildResults(query, meetings, T)

  // Clamp selected index when results change
  useEffect(() => {
    setSelected(prev => Math.min(prev, Math.max(0, results.length - 1)))
  }, [results.length])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handler = (e) => {
      if (e.key === 'Escape')    { setIsOpen(false) }
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(p => Math.min(p + 1, results.length - 1)) }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setSelected(p => Math.max(p - 1, 0)) }
      if (e.key === 'Enter' && results[selected]) {
        runAction(results[selected])
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, selected, results])

  const runAction = useCallback((item) => {
    setIsOpen(false)
    if (item.to) navigate(item.to)
    if (item.action) item.action()
  }, [navigate, setIsOpen])

  if (!isOpen) return null

  // createPortal renders this directly into document.body
  // so it always appears on top regardless of z-index context
  return createPortal(
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(8px)',
        zIndex: 10000,
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: 'clamp(60px, 12vh, 140px)',
        padding: 'clamp(60px, 12vh, 140px) 16px 0',
      }}
      onClick={e => { if (e.target === e.currentTarget) setIsOpen(false) }}
    >
      <div
        className="anim-scale-spring"
        style={{
          width: '100%', maxWidth: '580px',
          background: isDark ? 'rgba(13,17,32,0.97)' : 'rgba(255,255,255,0.97)',
          border: `1px solid ${isDark ? 'rgba(16,185,129,0.20)' : 'rgba(5,150,105,0.16)'}`,
          borderRadius: '18px',
          boxShadow: isDark
            ? '0 24px 72px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04) inset'
            : '0 24px 64px rgba(0,0,0,0.16)',
          overflow: 'hidden',
          maxHeight: '480px',
          display: 'flex', flexDirection: 'column',
        }}
      >
        {/* Search input */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '12px',
          padding: '16px 18px',
          borderBottom: `1px solid ${T.border}`,
        }}>
          <span style={{ fontSize: '18px', opacity: 0.5 }}>🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0) }}
            placeholder="Search meetings, navigate, or run actions…"
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              fontSize: '16px', color: T.text, fontFamily: 'inherit',
            }}
          />
          <Kbd>Esc</Kbd>
        </div>

        {/* Results */}
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {results.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: T.text3, fontSize: '14px' }}>
              {loading ? 'Loading…' : query ? `No results for "${query}"` : 'Type to search or navigate'}
            </div>
          ) : (
            <ResultList results={results} selected={selected} onSelect={setSelected} onRun={runAction} T={T} isDark={isDark} />
          )}
        </div>

        {/* Footer hint */}
        <div style={{
          padding: '10px 16px',
          borderTop: `1px solid ${T.border}`,
          display: 'flex', gap: '16px',
          fontSize: '11px', color: T.text3,
        }}>
          {[
            { key: '↑↓', label: 'navigate' },
            { key: '↵',  label: 'select'   },
            { key: 'Esc',label: 'close'    },
          ].map(h => (
            <div key={h.key} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Kbd>{h.key}</Kbd> {h.label}
            </div>
          ))}
        </div>
      </div>
    </div>,
    document.body
  )
}

// ── Result list ───────────────────────────────────────────────────────────────
function ResultList({ results, selected, onSelect, onRun, T, isDark }) {
  const selectedRef = useRef(null)

  // Scroll selected item into view automatically
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selected])

  // Group items by their group label
  const groups = results.reduce((acc, item, idx) => {
    const g = item.group || 'Results'
    if (!acc[g]) acc[g] = []
    acc[g].push({ ...item, _idx: idx })
    return acc
  }, {})

  return (
    <div style={{ padding: '6px' }}>
      {Object.entries(groups).map(([group, items]) => (
        <div key={group}>
          <div style={{
            padding: '8px 12px 4px',
            fontSize: '10.5px', fontWeight: 700,
            letterSpacing: '0.10em', textTransform: 'uppercase',
            color: T.text3,
          }}>
            {group}
          </div>
          {items.map(item => {
            const isSelected = item._idx === selected
            return (
              <div
                key={item.id}
                ref={isSelected ? selectedRef : null}
                onClick={() => onRun(item)}
                onMouseEnter={() => onSelect(item._idx)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  padding: '10px 12px',
                  borderRadius: '10px',
                  background: isSelected
                    ? T.accentBg
                    : 'transparent',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                }}
              >
                <span style={{ fontSize: '17px', flexShrink: 0 }}>{item.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '14px', fontWeight: 500,
                    color: isSelected ? T.accentLight : T.text,
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {item.label}
                  </div>
                  {item.subtitle && (
                    <div style={{ fontSize: '11.5px', color: T.text3, marginTop: '1px' }}>
                      {item.subtitle}
                    </div>
                  )}
                </div>
                {isSelected && (
                  <span style={{ fontSize: '11px', color: T.text3, flexShrink: 0 }}>↵</span>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}

// ── Build results from query + meetings ───────────────────────────────────────
function buildResults(query, meetings, T) {
  const q = query.toLowerCase().trim()

  if (!q) {
    // No query — show pages only
    return PAGES.slice(0, 6)
  }

  const results = []

  // Filter pages
  PAGES.forEach(p => {
    if (p.label.toLowerCase().includes(q) || p.id.includes(q)) {
      results.push(p)
    }
  })

  // Filter meetings
  meetings
    .filter(m => (m.filename || '').toLowerCase().includes(q))
    .slice(0, 6)
    .forEach(m => {
      results.push({
        id:       `meeting-${m.id}`,
        label:    m.filename || 'Untitled Meeting',
        icon:     '🎙️',
        subtitle: m.created_at ? new Date(m.created_at).toLocaleDateString() : '',
        to:       `/app/meetings/${m.id}`,
        group:    'Meetings',
      })
    })

  return results
}