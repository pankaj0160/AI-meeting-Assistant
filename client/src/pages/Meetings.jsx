// client/src/pages/Meetings.jsx

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, Search, ArrowRight, Mic, Clock, Calendar } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeetings } from '../api/client'
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

  // FIX: load first page on mount
  useEffect(() => {
    getMeetings({ limit: 20 })
      .then(data => {
        setMeetings(data.items || [])
        setHasMore(data.has_more || false)
        setCursor(data.next_cursor || null)
      })
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false))
  }, [])

  // FIX: load next page — appends to existing list
  const loadMore = async () => {
    if (!cursor || loadingMore) return
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
        subtitle={`${meetings.length} meeting${meetings.length !== 1 ? 's' : ''} processed`}
        action={
          <Button onClick={() => navigate('/app/upload')} icon={<Mic size={15} />}>
            New Meeting
          </Button>
        }
      />

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
            title={query ? 'No results found' : 'No meetings yet'}
            subtitle={query
              ? `No meetings match "${query}"`
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

        {/* Date — icon and text baseline-aligned with 8px gap */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          fontSize: '13px', color: T.text3, fontWeight: 400,
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
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
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