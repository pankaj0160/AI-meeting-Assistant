// client/src/pages/Meetings.jsx

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, Search, ArrowRight, Mic, Clock, Calendar, X } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeetings, getWorkspaceMeetings } from '../api/client'
import { useWorkspace } from '../context/WorkspaceContext'
import {
  PageHeader, Card, Button,
  EmptyState, Skeleton, Badge
} from '../components/ui'

// ── Spacing scale (px) ────────────────────────────────────────────────────────
// sp1=4  sp2=8  sp3=12  sp4=16  sp5=20  sp6=24  sp7=28  sp8=32  sp10=40
// Using these consistently keeps vertical rhythm uniform across the page.

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch { return iso.slice(0, 10) }
}

export default function Meetings() {
  const { T } = useTheme()
  const navigate = useNavigate()

  // FIX: Meetings used to always show every meeting on the account, with no
  // awareness of the workspace picked in the Sidebar switcher. It now reads
  // `activeWorkspaceId` from the shared WorkspaceContext:
  //   - null            → account-wide, paginated list (original behavior)
  //   - a workspace id  → only that workspace's meetings, via
  //                       GET /workspaces/{id}/meetings (returns everything
  //                       in one response — that endpoint has no pagination,
  //                       so "Load more" is disabled in this mode).
  const { activeWorkspaceId, activeWorkspace, selectWorkspace } = useWorkspace() || {}

  // FIX: Pagination state.
  // meetings   = array that grows as user loads more pages
  // cursor     = id of the last item we loaded (sent to server for next page)
  // hasMore    = whether server says there are more pages
  // loadingMore = true only when loading additional pages (not the first)
  const [meetings,    setMeetings]    = useState([])
  const [loading,     setLoading]     = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [cursor,      setCursor]      = useState(null)
  const [hasMore,     setHasMore]     = useState(false)
  const [query,       setQuery]       = useState('')

  // FIX: re-run whenever the active workspace changes, not just on mount.
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setCursor(null)
    setHasMore(false)

    const load = activeWorkspaceId != null
      ? getWorkspaceMeetings(activeWorkspaceId).then(data => ({
          items: data.meetings || [],
          has_more: false,      // workspace endpoint returns everything at once
          next_cursor: null,
        }))
      : getMeetings({ limit: 20 })

    load
      .then(data => {
        if (cancelled) return
        setMeetings(data.items || [])
        setHasMore(data.has_more || false)
        setCursor(data.next_cursor || null)
      })
      .catch(() => { if (!cancelled) setMeetings([]) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [activeWorkspaceId])

  // FIX: load next page — appends to existing list. Only applies in the
  // account-wide view; the workspace-filtered view loads everything up front.
  const loadMore = async () => {
    if (!cursor || loadingMore || activeWorkspaceId != null) return
    setLoadingMore(true)
    try {
      const data = await getMeetings({ cursor, limit: 20 })
      setMeetings(prev => [...prev, ...(data.items || [])])
      setHasMore(data.has_more || false)
      setCursor(data.next_cursor || null)
    } catch {
      // silently fail — user can retry
    } finally {
      setLoadingMore(false)
    }
  }

  const filtered = meetings.filter(m =>
    (m.filename || '').toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div>
      <PageHeader
        title="Meetings"
        eyebrow={activeWorkspace ? activeWorkspace.name : undefined}
        subtitle={loading
          ? 'Loading...'
          : `${meetings.length} meeting${meetings.length !== 1 ? 's' : ''}${activeWorkspace ? ` in ${activeWorkspace.name}` : ' processed'}`
        }
        action={
          <Button onClick={() => navigate('/app/upload')} icon={<Mic size={15} />}>
            New Meeting
          </Button>
        }
      />

      {/* FIX: makes it obvious a filter is active and gives a one-click way
          to clear it, instead of silently showing a subset of meetings. */}
      {activeWorkspace && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: '6px 10px 6px 12px', borderRadius: '99px', marginBottom: '20px',
          background: `${activeWorkspace.color || '#10b981'}14`,
          border: `1px solid ${activeWorkspace.color || '#10b981'}33`,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: activeWorkspace.color || '#10b981',
          }} />
          <span style={{ fontSize: '12.5px', fontWeight: 600, color: T.text2 }}>
            Filtered to <strong>{activeWorkspace.name}</strong>
          </span>
          <button
            onClick={() => selectWorkspace?.(null)}
            title="Clear workspace filter — show all meetings"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 18, height: 18, borderRadius: '50%',
              background: 'none', border: 'none', cursor: 'pointer',
              color: T.text3,
            }}
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* ── Search ──────────────────────────────────────────────────────────── */}
      {/* mb:28 gives clear separation between search bar and the card below   */}
      <div style={{ position: 'relative', marginBottom: '28px', maxWidth: '420px' }}>
        <Search
          size={16} color={T.text3}
          style={{
            position: 'absolute', left: '14px',
            top: '50%', transform: 'translateY(-50%)',
          }}
        />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search meetings..."
          style={{
            width: '100%',
            padding: '11px 16px 11px 42px',  // 11px top/bottom = 40px input height
            borderRadius: '10px',
            border: `1px solid ${T.inputBorder}`,
            background: T.inputBg,
            color: T.text,
            fontSize: '14px',
            outline: 'none',
            transition: 'border-color 0.15s ease',
          }}
          onFocus={e => e.target.style.borderColor = T.borderFocus}
          onBlur={e => e.target.style.borderColor = T.inputBorder}
        />
      </div>

      {/* ── List card ───────────────────────────────────────────────────────── */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          // Skeleton: 20px outer padding, 16px gap between skeleton rows
          <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[1, 2, 3, 4].map(i => (
              <div
                key={i}
                style={{
                  display: 'flex', gap: '12px',
                  alignItems: 'center',
                  padding: '6px 0', // 6px top/bottom keeps rows at ~56px total
                }}
              >
                <Skeleton width="44px" height="44px" style={{ borderRadius: '10px', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <Skeleton width="55%" height="15px" style={{ marginBottom: '8px' }} />
                  <Skeleton width="30%" height="12px" />
                </div>
                <Skeleton width="80px" height="26px" style={{ borderRadius: '99px' }} />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="🎙️"
            title={query ? 'No results found' : activeWorkspace ? `No meetings in ${activeWorkspace.name}` : 'No meetings yet'}
            subtitle={query
              ? `No meetings match "${query}"`
              : activeWorkspace
                ? 'Open a meeting and use its Workspace button to add it here.'
                : 'Upload your first meeting recording to get started.'
            }
            action={!query &&
              <Button icon={<Mic size={15} />} onClick={() => navigate('/app/upload')}>
                Upload Meeting
              </Button>
            }
          />
        ) : (
          <div>
            {/* Table header — 14px vertical padding gives clear label height    */}
            {/* without competing visually with the data rows below               */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 140px 110px 130px 44px',
              gap: '16px',
              padding: '14px 24px',
              borderBottom: `1px solid ${T.border}`,
            }}>
              {['Meeting', 'Date', 'ID', 'Status', ''].map(h => (
                <div key={h} style={{
                  fontSize: '11px', fontWeight: 700,
                  letterSpacing: '0.08em', textTransform: 'uppercase',
                  color: T.text3,
                }}>
                  {h}
                </div>
              ))}
            </div>

            {/* Rows */}
            {filtered.map((m, i) => (
              <MeetingRow
                key={m.id}
                meeting={m}
                delay={i * 0.04}
                onClick={() => navigate(`/app/meetings/${m.id}`)}
                T={T}
              />
            ))}

            {/* FIX: Load more button — only shown when more pages exist */}
            {hasMore && !query && (
              <div style={{ padding: '20px 24px', borderTop: `1px solid ${T.border}` }}>
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  style={{
                    width: '100%',
                    padding: '10px',
                    borderRadius: '10px',
                    border: `1px solid ${T.border}`,
                    background: T.surface,
                    color: T.text2,
                    fontSize: '13.5px',
                    fontWeight: 500,
                    cursor: loadingMore ? 'not-allowed' : 'pointer',
                    opacity: loadingMore ? 0.6 : 1,
                    fontFamily: 'var(--font)',
                    transition: 'all 0.15s',
                  }}
                >
                  {loadingMore ? 'Loading...' : 'Load more meetings'}
                </button>
              </div>
            )}

            {!hasMore && meetings.length > 0 && !query && (
              <div style={{
                padding: '16px 24px',
                textAlign: 'center',
                fontSize: '12px',
                color: T.text3,
                borderTop: `1px solid ${T.border}`,
              }}>
                All {meetings.length} meetings loaded
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

function MeetingRow({ meeting, onClick, delay, T }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className="anim-fade-up"
      style={{ animationDelay: `${delay}s` }}
    >
      <div
        onClick={onClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        role="button"
        tabIndex={0}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 140px 110px 130px 44px',
          gap: '16px',
          // 18px top/bottom: enough breathing room between rows without
          // making the list feel too spacious for dense data
          padding: '18px 24px',
          alignItems: 'center',
          cursor: 'pointer',
          background: hovered ? T.surfaceHover : 'transparent',
          borderBottom: `1px solid ${T.border}`,
          transition: 'background 0.15s ease',
        }}
      >
        {/* Meeting name */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
          {/* Icon container: 40x40 with internal centering */}
          <div style={{
            width: '40px', height: '40px',
            borderRadius: '10px',
            background: T.accentBg,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Mic size={17} color={T.accentLight} strokeWidth={2} />
          </div>
          <div style={{
            fontSize: '15px', fontWeight: 600,
            color: T.text, letterSpacing: '-0.02em',
            whiteSpace: 'nowrap', overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {meeting.filename || 'Untitled Meeting'}
          </div>
        </div>

        {/* Date — icon and text baseline-aligned with 8px gap.
            Mono face here (not body Inter) because this is metadata about
            timestamped data — consistent with meeting ID and transcript
            timestamps below, reinforces the "this is structured data" read. */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontFamily: 'var(--font-mono, var(--font))',
          fontSize: '12px', color: T.text3, fontWeight: 400,
        }}>
          <Calendar size={13} color={T.text4} />
          {fmt(meeting.created_at)}
        </div>

        {/* Meeting ID — monospace pill, truncated to first 8 chars */}
        <div style={{
          display: 'inline-flex', alignItems: 'center',
          maxWidth: '110px',
        }}>
          <span style={{
            fontSize: '11.5px',
            fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace)',
            color: T.text3,
            background: T.surface2,
            border: `1px solid ${T.border}`,
            borderRadius: '6px',
            padding: '3px 8px',
            letterSpacing: '0.02em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '100%',
            display: 'block',
          }}>
            {String(meeting.id).length > 8
              ? String(meeting.id).slice(0, 8) + '…'
              : String(meeting.id)
            }
          </span>
        </div>

        {/* Status badge */}
        <div>
          <Badge color={T.emeraldText} bg={T.emeraldBg}>
            Processed
          </Badge>
        </div>

        {/* Arrow — appears on hover */}
        <div style={{
          display: 'flex', justifyContent: 'center',
          opacity: hovered ? 1 : 0,
          transition: 'opacity 0.15s ease',
        }}>
          <ArrowRight size={16} color={T.text3} />
        </div>
      </div>
    </div>
  )
}