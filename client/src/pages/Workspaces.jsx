// client/src/pages/Workspaces.jsx
//
// WHAT THIS PAGE DOES:
// ────────────────────
// Shows all workspaces the user owns or is a member of.
// A workspace is a folder that groups related meetings together.
//
// EXAMPLE USE CASES:
//   "Q3 Product Planning" workspace → all sprint planning meetings in one place
//   "Sales Team" workspace → all sales call recordings
//   "Personal" workspace → your own 1:1s and solo recordings
//
// YOUR BACKEND ALREADY HAS:
//   GET  /workspaces               → list all workspaces
//   POST /workspaces               → create new workspace
//   GET  /workspaces/{id}          → single workspace details
//   GET  /workspaces/{id}/meetings → meetings inside a workspace
//   GET  /workspaces/{id}/members  → who is in the workspace
//   POST /workspaces/{id}/members  → invite someone by email
//
// This page has THREE views:
//   1. Grid of workspace cards (the list view — default)
//   2. Create workspace modal (inline, no separate page)
//   3. Workspace detail view (expands inline when you click a card)
//
// WHY INLINE DETAIL instead of a separate /workspaces/:id route?
//   Keeps navigation simple. User sees meetings inside a workspace
//   without losing their place in the workspace list.
//   Large meeting list → still navigates to /app/meetings/:id for full detail.

import { useState, useEffect, useCallback } from 'react'
import { useNavigate }                       from 'react-router-dom'
import {
  Folder, FolderOpen, Plus, Users, FileText,
  ChevronRight, ArrowLeft, Settings, UserPlus,
  Trash2, X, Check, AlertCircle, RefreshCw,
  Lock, Globe, MoreHorizontal, Star,
} from 'lucide-react'
import { useTheme }    from '../ThemeContext'
import { useToast }    from '../components/Toast'
import {
  PageHeader, Card, Button, EmptyState, Skeleton, Badge,
} from '../components/ui'
import {
  createWorkspace,
  getWorkspace, getWorkspaceMeetings,
  getWorkspaceMembers, inviteMember,
  deleteWorkspace,
} from '../api/client'
// FIX: previously this page managed its own local `workspaces` state and had
// zero connection to the rest of the app — picking a workspace here did
// nothing anywhere else. It now reads/writes the shared WorkspaceContext so
// the Sidebar switcher, Meetings filter, and this page all stay in sync.
import { useWorkspace } from '../context/WorkspaceContext'

// ── Workspace colour palette ──────────────────────────────────────────────────
// Each workspace picks a colour when created. We show it as a left-border
// accent and as the folder icon tint.
const WORKSPACE_COLORS = [
  { value: '#10b981', label: 'Emerald' },
  { value: '#3b82f6', label: 'Blue'    },
  { value: '#f97316', label: 'Orange'  },
  { value: '#f59e0b', label: 'Amber'   },
  { value: '#06b6d4', label: 'Cyan'    },
  { value: '#ef4444', label: 'Red'     },
  { value: '#a855f7', label: 'Purple'  },
  { value: '#6366f1', label: 'Indigo'  },
]

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch { return '—' }
}

// ── Create Workspace Modal ────────────────────────────────────────────────────
function CreateModal({ onClose, onCreate, T, isDark }) {
  const [name,   setName]   = useState('')
  const [desc,   setDesc]   = useState('')
  const [color,  setColor]  = useState('#10b981')
  const [type,   setType]   = useState('individual')
  const [saving, setSaving] = useState(false)
  const [err,    setErr]    = useState('')

  async function handleSubmit() {
    if (!name.trim()) { setErr('Workspace name is required.'); return }
    setSaving(true)
    setErr('')
    try {
      const ws = await createWorkspace(name.trim(), desc.trim(), type, color)
      onCreate(ws)
      onClose()
    } catch (e) {
      setErr(e.message || 'Failed to create workspace.')
    } finally {
      setSaving(false)
    }
  }

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.70)',
      backdropFilter: 'blur(10px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 800, padding: '24px',
    }}>
      <div className="anim-scale-spring" style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: '20px',
        width: '100%', maxWidth: '480px',
        boxShadow: '0 32px 80px rgba(0,0,0,0.45)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: `1px solid ${T.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: 36, height: 36, borderRadius: '10px',
              background: T.accentBg,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Folder size={17} color={T.accent} />
            </div>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>
                New Workspace
              </div>
              <div style={{ fontSize: '12px', color: T.text3 }}>
                Group meetings by project or team
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            width: 30, height: 30, borderRadius: '8px',
            background: T.surface2, border: `1px solid ${T.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: T.text3, fontFamily: 'inherit',
            fontSize: '18px', lineHeight: 1,
          }}>×</button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>

          {/* Error */}
          {err && (
            <div style={{
              padding: '10px 14px', borderRadius: '10px',
              background: `${T.danger}12`,
              border: `1px solid ${T.danger}33`,
              display: 'flex', alignItems: 'center', gap: '8px',
              fontSize: '13px', color: T.danger,
            }}>
              <AlertCircle size={14} />
              {err}
            </div>
          )}

          {/* Name */}
          <div>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 650, color: T.text2, marginBottom: '7px' }}>
              Workspace Name *
            </label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="e.g. Q3 Product Planning"
              autoFocus
              style={{
                width: '100%', padding: '10px 14px',
                borderRadius: '10px',
                border: `1px solid ${T.border}`,
                background: T.surface2, color: T.text,
                fontSize: '14px', outline: 'none',
                fontFamily: 'inherit',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={e => e.target.style.borderColor = T.accent}
              onBlur={e  => e.target.style.borderColor = T.border}
            />
          </div>

          {/* Description */}
          <div>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 650, color: T.text2, marginBottom: '7px' }}>
              Description <span style={{ fontWeight: 400, color: T.text4 }}>(optional)</span>
            </label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="What kind of meetings go in here?"
              rows={2}
              style={{
                width: '100%', padding: '10px 14px',
                borderRadius: '10px',
                border: `1px solid ${T.border}`,
                background: T.surface2, color: T.text,
                fontSize: '14px', outline: 'none',
                fontFamily: 'inherit', resize: 'none',
                lineHeight: 1.6,
                transition: 'border-color 0.15s ease',
              }}
              onFocus={e => e.target.style.borderColor = T.accent}
              onBlur={e  => e.target.style.borderColor = T.border}
            />
          </div>

          {/* Type — individual or project */}
          <div>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 650, color: T.text2, marginBottom: '7px' }}>
              Type
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {[
                { id: 'individual', label: 'Personal',     icon: <Lock size={13}/>,  desc: 'Just you' },
                { id: 'project',    label: 'Team Project', icon: <Users size={13}/>, desc: 'Invite others' },
              ].map(opt => (
                <div
                  key={opt.id}
                  onClick={() => setType(opt.id)}
                  role="button"
                  tabIndex={0}
                  aria-pressed={type === opt.id}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setType(opt.id) } }}
                  style={{
                    flex: 1, padding: '10px 14px',
                    borderRadius: '10px', cursor: 'pointer',
                    border: `1.5px solid ${type === opt.id ? T.accent : T.border}`,
                    background: type === opt.id ? T.accentBg : T.surface2,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
                    <span style={{ color: type === opt.id ? T.accent : T.text3 }}>{opt.icon}</span>
                    <span style={{ fontSize: '13px', fontWeight: 650, color: type === opt.id ? T.accent : T.text }}>
                      {opt.label}
                    </span>
                  </div>
                  <div style={{ fontSize: '11px', color: T.text4 }}>{opt.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Color picker */}
          <div>
            <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 650, color: T.text2, marginBottom: '10px' }}>
              Color
            </label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {WORKSPACE_COLORS.map(c => (
                <button
                  key={c.value}
                  title={c.label}
                  onClick={() => setColor(c.value)}
                  style={{
                    width: 26, height: 26, borderRadius: '50%',
                    background: c.value, border: 'none', cursor: 'pointer',
                    // Was `outline` for the selected-state ring, which
                    // hardcoded outline to transparent for every unselected
                    // swatch and silently blocked the keyboard focus-visible
                    // ring underneath it. box-shadow achieves the same look
                    // without touching outline.
                    boxShadow: color === c.value ? `0 0 0 2px ${T.surface}, 0 0 0 4px ${c.value}` : 'none',
                    transition: 'box-shadow 0.12s ease, transform 0.12s ease',
                    transform: color === c.value ? 'scale(1.15)' : 'scale(1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  {color === c.value && <Check size={11} color="#fff" strokeWidth={3} />}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: `1px solid ${T.border}`,
          display: 'flex', gap: '10px', justifyContent: 'flex-end',
        }}>
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleSubmit} loading={saving}>
            Create Workspace
          </Button>
        </div>
      </div>
    </div>
  )
}

// ── Workspace Card ────────────────────────────────────────────────────────────
// FIX: added `isActive` + `onSetActive` — the card now shows whether it's the
// workspace currently selected app-wide (in the Sidebar switcher), and lets
// you set/unset it as active without opening the full detail view.
function WorkspaceCard({ ws, onClick, onDelete, onSetActive, isActive, T }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const color = ws.color || '#10b981'

  return (
    <div
      style={{ position: 'relative' }}
      onMouseLeave={() => setMenuOpen(false)}
    >
      <Card
        hoverable
        onClick={onClick}
        style={{
          borderLeft: `3px solid ${color}`,
          cursor: 'pointer',
          boxShadow: isActive ? `0 0 0 1.5px ${color}66` : undefined,
        }}
      >
        {isActive && (
          <div style={{
            position: 'absolute', left: '14px', top: '-8px',
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '2px 8px', borderRadius: '99px',
            background: color, color: '#fff',
            fontSize: '10px', fontWeight: 700, letterSpacing: '0.04em',
            boxShadow: `0 2px 8px ${color}66`,
          }}>
            <Star size={9} fill="#fff" /> ACTIVE
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>

          {/* Icon + info */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', flex: 1, minWidth: 0 }}>
            <div style={{
              width: 40, height: 40, borderRadius: '11px',
              background: `${color}18`,
              border: `1px solid ${color}33`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Folder size={18} color={color} />
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: '15px', fontWeight: 700, color: T.text,
                letterSpacing: '-0.02em', marginBottom: '4px',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {ws.name}
              </div>
              {ws.description && (
                <div style={{
                  fontSize: '12.5px', color: T.text3,
                  lineHeight: 1.5, marginBottom: '10px',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {ws.description}
                </div>
              )}

              {/* Stats row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: T.text3 }}>
                  <FileText size={11} color={T.text4} />
                  {ws.meeting_count ?? 0} meetings
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: T.text3 }}>
                  <Users size={11} color={T.text4} />
                  {ws.member_count ?? 1} member{(ws.member_count ?? 1) !== 1 ? 's' : ''}
                </span>
                <span style={{ fontSize: '12px', color: T.text4 }}>
                  {fmt(ws.created_at)}
                </span>
              </div>
            </div>
          </div>

          {/* Right: type badge + menu */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <Badge
              color={ws.type === 'project' ? T.purpleText : T.text3}
              bg={ws.type === 'project' ? T.purpleBg : T.surface2}
            >
              {ws.type === 'project' ? '👥 Team' : '🔒 Personal'}
            </Badge>

            {/* ⋯ menu button */}
            <button
              onClick={e => { e.stopPropagation(); setMenuOpen(v => !v) }}
              style={{
                width: 28, height: 28, borderRadius: '7px',
                background: menuOpen ? T.surface2 : 'transparent',
                border: `1px solid ${menuOpen ? T.border : 'transparent'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: T.text3,
                transition: 'all 0.12s ease',
              }}
            >
              <MoreHorizontal size={14} />
            </button>
          </div>
        </div>

        {/* Arrow */}
        <div style={{
          position: 'absolute', right: '18px', bottom: '18px',
          display: 'flex', alignItems: 'center', gap: '4px',
          fontSize: '12px', color: T.text4, fontWeight: 500,
        }}>
          Open <ChevronRight size={13} />
        </div>
      </Card>

      {/* Dropdown menu */}
      {menuOpen && (
        <div
          className="anim-fade-down"
          style={{
            position: 'absolute', top: '14px', right: '14px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: '10px',
            boxShadow: '0 8px 28px rgba(0,0,0,0.22)',
            zIndex: 50, minWidth: '160px',
            overflow: 'hidden',
          }}
          onClick={e => e.stopPropagation()}
        >
          <button
            onClick={() => { setMenuOpen(false); onSetActive(ws) }}
            style={{
              width: '100%', padding: '10px 14px',
              background: 'none', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '8px',
              fontSize: '13px', color: T.text,
              fontFamily: 'inherit', textAlign: 'left',
              transition: 'background 0.1s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.background = T.surface2}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}
          >
            <Star size={13} color={color} /> {isActive ? 'Unset as active' : 'Set as active'}
          </button>
          <div style={{ height: 1, background: T.border }} />
          <button
            onClick={() => { setMenuOpen(false); onDelete(ws) }}
            style={{
              width: '100%', padding: '10px 14px',
              background: 'none', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '8px',
              fontSize: '13px', color: T.danger,
              fontFamily: 'inherit', textAlign: 'left',
              transition: 'background 0.1s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.background = `${T.danger}12`}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}
          >
            <Trash2 size={13} /> Delete workspace
          </button>
        </div>
      )}
    </div>
  )
}

// ── Workspace Detail Panel ────────────────────────────────────────────────────
// Shows meetings and members inside a selected workspace.
// Slides in inline — no navigation to a new page.
function WorkspaceDetail({ wsId, onBack, T }) {
  const navigate = useNavigate()
  const { toast } = useToast()
  // FIX: the detail view previously had no way to make this the app-wide
  // active workspace — you had to go back to the grid and use the card menu.
  const { activeWorkspaceId, selectWorkspace } = useWorkspace() || {}
  const isActive = activeWorkspaceId === wsId

  const [ws,       setWs]       = useState(null)
  const [meetings, setMeetings] = useState([])
  const [members,  setMembers]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviting,    setInviting]    = useState(false)
  const [activeTab,   setActiveTab]   = useState('meetings')

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [wsRes, meetRes, memRes] = await Promise.allSettled([
          getWorkspace(wsId),
          getWorkspaceMeetings(wsId),
          getWorkspaceMembers(wsId),
        ])
        if (wsRes.status   === 'fulfilled') setWs(wsRes.value)
        if (meetRes.status === 'fulfilled') {
          const data = meetRes.value
          setMeetings(Array.isArray(data) ? data : (data.items || []))
        }
        // Backend returns { total, members: [...] } for this endpoint, not a
        // bare array — same shape mismatch pattern as meetings above. Without
        // unwrapping, `memRes.value || []` kept the whole object (truthy),
        // and members.map() crashed the page.
        if (memRes.status  === 'fulfilled') {
          const data = memRes.value
          setMembers(Array.isArray(data) ? data : (data?.members || []))
        }
      } catch (e) {
        toast.error('Failed to load workspace', e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [wsId])

  async function handleInvite() {
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      await inviteMember(wsId, inviteEmail.trim())
      toast.success('Invitation sent', `${inviteEmail} was invited to the workspace.`)
      setInviteEmail('')
      // Refresh members — same unwrap as the initial load, see comment above
      const mem = await getWorkspaceMembers(wsId)
      setMembers(Array.isArray(mem) ? mem : (mem?.members || []))
    } catch (e) {
      toast.error('Invite failed', e.message)
    } finally {
      setInviting(false)
    }
  }

  const color = ws?.color || '#10b981'

  return (
    <div className="page-enter">

      {/* Back button */}
      <button
        onClick={onBack}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          fontSize: '13px', fontWeight: 600, color: T.text3,
          background: 'none', border: 'none', cursor: 'pointer',
          marginBottom: '20px', padding: 0,
          transition: 'color 0.12s ease', fontFamily: 'inherit',
        }}
        onMouseEnter={e => e.currentTarget.style.color = T.text}
        onMouseLeave={e => e.currentTarget.style.color = T.text3}
      >
        <ArrowLeft size={14} /> All Workspaces
      </button>

      {/* Header */}
      {loading ? (
        <div style={{ marginBottom: '28px' }}>
          <Skeleton width="40%" height="32px" style={{ marginBottom: '10px' }} />
          <Skeleton width="25%" height="14px" />
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px', marginBottom: '28px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: 48, height: 48, borderRadius: '13px',
              background: `${color}18`, border: `1.5px solid ${color}44`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <FolderOpen size={22} color={color} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h1 style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-0.04em', color: T.text, margin: 0 }}>
                  {ws?.name}
                </h1>
                {isActive && (
                  <Badge color="#fff" bg={color} dot={false}>
                    <Star size={9} fill="#fff" /> Active
                  </Badge>
                )}
              </div>
              {ws?.description && (
                <div style={{ fontSize: '13px', color: T.text3, marginTop: '4px' }}>{ws.description}</div>
              )}
            </div>
          </div>

          {/* FIX: set/unset this workspace as the app-wide active one directly
              from the detail view, without going back to the grid. */}
          <Button
            variant={isActive ? 'secondary' : 'primary'}
            size="sm"
            icon={<Star size={13} fill={isActive ? 'currentColor' : 'none'} />}
            onClick={() => selectWorkspace?.(isActive ? null : wsId)}
          >
            {isActive ? 'Unset as Active' : 'Set as Active'}
          </Button>
        </div>
      )}

      {/* Stats strip */}
      {!loading && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '28px', flexWrap: 'wrap' }}>
          {[
            { label: 'Meetings', value: meetings.length, icon: '📁' },
            { label: 'Members',  value: members.length,  icon: '👥' },
            { label: 'Type',     value: ws?.type === 'project' ? 'Team' : 'Personal', icon: ws?.type === 'project' ? '🌐' : '🔒' },
          ].map(stat => (
            <div key={stat.label} style={{
              padding: '12px 18px', borderRadius: '12px',
              background: T.surface, border: `1px solid ${T.border}`,
              display: 'flex', alignItems: 'center', gap: '10px',
            }}>
              <span style={{ fontSize: '16px' }}>{stat.icon}</span>
              <div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: T.text, lineHeight: 1 }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: '11px', color: T.text3, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  {stat.label}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '20px' }}>
        {[
          { id: 'meetings', label: `Meetings (${meetings.length})` },
          { id: 'members',  label: `Members (${members.length})`  },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px', borderRadius: '8px',
              fontSize: '13px', fontWeight: 600,
              background: activeTab === tab.id ? T.accentBg : 'transparent',
              border: `1px solid ${activeTab === tab.id ? T.accent + '44' : T.border}`,
              color: activeTab === tab.id ? T.accent : T.text3,
              cursor: 'pointer', fontFamily: 'inherit',
              transition: 'all 0.15s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Meetings tab */}
      {activeTab === 'meetings' && (
        <div>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {[1,2,3].map(i => <Skeleton key={i} height="72px" style={{ borderRadius: '12px' }} />)}
            </div>
          ) : meetings.length === 0 ? (
            <EmptyState
              icon="📁"
              title="No meetings yet"
              subtitle="Open any meeting and use its Workspace button to add it here."
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {meetings.map((m, i) => (
                <div
                  key={m.id}
                  className="anim-fade-up"
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  <Card
                    hoverable
                    onClick={() => navigate(`/app/meetings/${m.id}`)}
                    style={{ padding: '16px 20px', cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{
                        width: 34, height: 34, borderRadius: '9px',
                        background: T.blueBg, flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <FileText size={15} color={T.blueText} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: '14px', fontWeight: 600, color: T.text,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        }}>
                          {m.filename || 'Untitled Meeting'}
                        </div>
                        <div style={{ fontSize: '12px', color: T.text3, marginTop: '2px' }}>
                          {fmt(m.created_at)}
                        </div>
                      </div>
                      <ChevronRight size={14} color={T.text4} />
                    </div>
                  </Card>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Members tab */}
      {activeTab === 'members' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          {/* Invite form — only shown for project workspaces */}
          {ws?.type === 'project' && (
            <Card>
              <div style={{ fontSize: '14px', fontWeight: 700, color: T.text, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <UserPlus size={15} color={T.accent} />
                Invite Member
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleInvite()}
                  placeholder="colleague@company.com"
                  type="email"
                  style={{
                    flex: 1, padding: '9px 13px', borderRadius: '9px',
                    border: `1px solid ${T.border}`,
                    background: T.surface2, color: T.text,
                    fontSize: '13.5px', outline: 'none', fontFamily: 'inherit',
                  }}
                  onFocus={e => e.target.style.borderColor = T.accent}
                  onBlur={e  => e.target.style.borderColor = T.border}
                />
                <Button onClick={handleInvite} loading={inviting} size="sm">
                  Send Invite
                </Button>
              </div>
            </Card>
          )}

          {/* Members list */}
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[1,2].map(i => <Skeleton key={i} height="58px" style={{ borderRadius: '12px' }} />)}
            </div>
          ) : members.length === 0 ? (
            <EmptyState icon="👥" title="No members yet" subtitle="Invite teammates to collaborate on this workspace." />
          ) : (
            <Card style={{ padding: 0, overflow: 'hidden' }}>
              {members.map((mem, i) => (
                <div key={mem.id || i} style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  padding: '14px 20px',
                  borderBottom: i < members.length - 1 ? `1px solid ${T.border}` : 'none',
                }}>
                  {/* Avatar */}
                  <div style={{
                    width: 34, height: 34, borderRadius: '50%',
                    background: `linear-gradient(145deg,${T.accent},${T.accentLight})`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff', fontSize: '12px', fontWeight: 800, flexShrink: 0,
                  }}>
                    {(mem.full_name || mem.email || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '13.5px', fontWeight: 600, color: T.text }}>
                      {mem.full_name || mem.email}
                    </div>
                    {mem.email && mem.full_name && (
                      <div style={{ fontSize: '11.5px', color: T.text3 }}>{mem.email}</div>
                    )}
                  </div>
                  <Badge
                    color={mem.role === 'owner' ? T.accent : T.text3}
                    bg={mem.role === 'owner' ? T.accentBg : T.surface2}
                  >
                    {mem.role || 'member'}
                  </Badge>
                </div>
              ))}
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
// FIX: This page used to keep its own local `workspaces` list, completely
// disconnected from the rest of the app — nothing else ever knew what you
// clicked here. It now reads/writes the shared WorkspaceContext:
//   - `workspaces` and `loading` come straight from context (single source
//     of truth, same list the Sidebar switcher shows).
//   - create/delete update context via upsertWorkspace/removeWorkspaceLocal
//     so the Sidebar reflects changes immediately, without a full refetch.
//   - `activeWorkspaceId`/`selectWorkspace` let cards show which workspace
//     is currently active app-wide and let you change it from here.
export default function Workspaces() {
  const { T, isDark }     = useTheme()
  const { toast }         = useToast()
  const {
    workspaces, loading, activeWorkspaceId,
    selectWorkspace, refreshWorkspaces,
    upsertWorkspace, removeWorkspaceLocal,
  } = useWorkspace() || {}

  const [error,          setError]          = useState(null)
  const [showCreate,     setShowCreate]     = useState(false)
  const [selectedWsId,   setSelectedWsId]   = useState(null)
  const [confirmDelete,  setConfirmDelete]  = useState(null)   // ws to delete

  const load = useCallback(async () => {
    setError(null)
    try {
      await refreshWorkspaces?.()
    } catch (e) {
      setError(e.message)
    }
  }, [refreshWorkspaces])

  useEffect(() => { load() }, [load])

  function handleCreated(ws) {
    upsertWorkspace?.(ws)
    toast.success('Workspace created', `"${ws.name}" is ready.`)
  }

  async function handleDelete(ws) {
    setConfirmDelete(null)
    try {
      await deleteWorkspace(ws.id)
      removeWorkspaceLocal?.(ws.id)
      toast.success('Workspace deleted', `"${ws.name}" was removed.`)
      if (selectedWsId === ws.id) setSelectedWsId(null)
    } catch (e) {
      toast.error('Delete failed', e.message)
    }
  }

  function handleSetActive(ws) {
    const willActivate = activeWorkspaceId !== ws.id
    selectWorkspace?.(willActivate ? ws.id : null)
    toast.success(
      willActivate ? 'Active workspace set' : 'Active workspace cleared',
      willActivate
        ? `"${ws.name}" is now shown across the app.`
        : 'Switched back to All Meetings.',
    )
  }

  // ── If a workspace is selected, show its detail panel ──────────────────────
  if (selectedWsId) {
    return (
      <WorkspaceDetail
        wsId={selectedWsId}
        onBack={() => setSelectedWsId(null)}
        T={T}
        isDark={isDark}
      />
    )
  }

  // ── Main grid view ─────────────────────────────────────────────────────────
  return (
    <div>
      <PageHeader
        title="Workspaces"
        eyebrow="Organisation"
        subtitle={loading ? 'Loading...' : `${(workspaces || []).length} workspace${(workspaces || []).length !== 1 ? 's' : ''}`}
        action={
          <Button icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>
            New Workspace
          </Button>
        }
      />

      {/* Error */}
      {error && (
        <div style={{
          padding: '16px 20px', marginBottom: '20px',
          background: `${T.danger}10`, border: `1px solid ${T.danger}30`,
          borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '12px',
        }}>
          <AlertCircle size={16} color={T.danger} />
          <span style={{ fontSize: '13.5px', color: T.danger, flex: 1 }}>{error}</span>
          <Button size="sm" variant="ghost" icon={<RefreshCw size={12}/>} onClick={load}>Retry</Button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {[1,2,3].map(i => (
            <Card key={i}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <Skeleton width="40px" height="40px" style={{ borderRadius: '11px', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <Skeleton width="40%" height="16px" style={{ marginBottom: '8px' }} />
                  <Skeleton width="60%" height="12px" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && (workspaces || []).length === 0 && (
        <EmptyState
          icon="📁"
          title="No workspaces yet"
          subtitle="Create a workspace to group meetings by project or team."
          action={
            <Button icon={<Plus size={14}/>} onClick={() => setShowCreate(true)}>
              Create your first workspace
            </Button>
          }
        />
      )}

      {/* Workspace cards */}
      {!loading && (workspaces || []).length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {workspaces.map((ws, i) => (
            <div key={ws.id} className="anim-fade-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <WorkspaceCard
                ws={ws}
                T={T}
                isActive={activeWorkspaceId === ws.id}
                onSetActive={handleSetActive}
                onClick={() => setSelectedWsId(ws.id)}
                onDelete={ws => setConfirmDelete(ws)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateModal
          T={T}
          isDark={isDark}
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.65)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 800, padding: '24px',
        }}>
          <div className="anim-scale-spring" style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: '18px', width: '100%', maxWidth: '400px',
            padding: '28px', boxShadow: '0 24px 60px rgba(0,0,0,0.4)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 38, height: 38, borderRadius: '10px',
                background: `${T.danger}14`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Trash2 size={17} color={T.danger} />
              </div>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Delete Workspace</div>
                <div style={{ fontSize: '12px', color: T.text3 }}>This action cannot be undone.</div>
              </div>
            </div>
            <p style={{ fontSize: '13.5px', color: T.text2, lineHeight: 1.6, marginBottom: '24px' }}>
              Are you sure you want to delete <strong style={{ color: T.text }}>"{confirmDelete.name}"</strong>?
              The workspace will be removed, but the meetings inside it will not be deleted.
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <Button variant="ghost" onClick={() => setConfirmDelete(null)}>Cancel</Button>
              <Button
                onClick={() => handleDelete(confirmDelete)}
                style={{ background: T.danger, borderColor: T.danger }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}