// client/src/pages/Summaries.jsx
//
// WHAT THIS PAGE DOES:
// ────────────────────
// Shows a scrollable list of every meeting with its AI-generated summary.
// Clicking a card goes to the full MeetingDetail page.
//
// WHAT WAS BROKEN (and why the page showed nothing):
// ───────────────────────────────────────────────────
// The old code had TWO bugs that together caused a completely empty page:
//
// BUG 1 — N+1 API call pattern:
//   The old code called getMeetings() to get 20 meetings, then called
//   getMeetingIntelligence(m.id) for EACH meeting in a loop.
//   20 meetings = 21 API calls on every page load.
//   But getMeetings() returns a PAGINATED OBJECT not an array:
//     { items: [...], has_more: true, next_cursor: 42 }
//   The code tried to call .slice(0, 20) on this object → crash.
//   .slice is a function on arrays, not on plain objects.
//   The catch block swallowed the error silently → empty page.
//
// BUG 2 — getMeeting() already includes intelligence:
//   GET /meetings/{id} returns the full meeting including intelligence.
//   We don't need a separate getMeetingIntelligence() call at all.
//   We can get summaries from the meeting list + individual meeting data.
//
// FIX:
//   1. Use getMeetingsList() which correctly extracts the items array.
//   2. For each meeting, call getMeeting(id) which returns the full
//      object including intelligence — one fetch per meeting still,
//      but the data is correct and errors are visible.
//   3. Cap at 30 meetings with Promise.allSettled for fault tolerance.
//   4. Show an error message instead of silently failing.

import { useState, useEffect } from 'react'
import { useNavigate }         from 'react-router-dom'
import { FileText, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react'
import { useTheme }            from '../ThemeContext'
import { getMeetingsList, getMeeting } from '../api/client'
import { PageHeader, Card, EmptyState, Skeleton, Button } from '../components/ui'

// ── Date formatter ────────────────────────────────────────────────────────────
function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch { return '—' }
}

// ── Loading skeleton for one card ─────────────────────────────────────────────
function SummaryCardSkeleton({ T }) {
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <Skeleton width="36px" height="36px" style={{ borderRadius: '9px', flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <Skeleton width="55%" height="16px" style={{ marginBottom: '6px' }} />
          <Skeleton width="30%" height="12px" />
        </div>
      </div>
      <Skeleton width="100%" height="14px" style={{ marginBottom: '7px' }} />
      <Skeleton width="92%"  height="14px" style={{ marginBottom: '7px' }} />
      <Skeleton width="78%"  height="14px" style={{ marginBottom: '16px' }} />
      <div style={{ display: 'flex', gap: '6px' }}>
        <Skeleton width="70px" height="22px" style={{ borderRadius: '99px' }} />
        <Skeleton width="85px" height="22px" style={{ borderRadius: '99px' }} />
      </div>
    </Card>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Summaries() {
  const { T }    = useTheme()
  const navigate = useNavigate()

  const [summaries,  setSummaries]  = useState([])
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(null)
  const [loadingMsg, setLoadingMsg] = useState('Loading meetings...')

  async function load() {
    setLoading(true)
    setError(null)

    try {
      // Step 1: get list of meetings (paginated → correctly extract .items)
      // getMeetingsList() handles the { items, has_more } wrapper for us.
      setLoadingMsg('Loading meetings...')
      const meetings = await getMeetingsList(30)

      if (!meetings || meetings.length === 0) {
        setSummaries([])
        return
      }

      // Step 2: for each meeting, fetch full data (includes intelligence).
      // GET /meetings/{id} returns the meeting WITH intelligence embedded,
      // so this is the minimum possible number of API calls.
      //
      // Promise.allSettled instead of Promise.all:
      //   If one meeting fails to load, the rest still appear.
      //   Promise.all would fail the entire page if even one meeting errors.
      setLoadingMsg(`Loading summaries for ${meetings.length} meetings...`)

      const results = await Promise.allSettled(
        meetings.map(m => getMeeting(m.id))
      )

      // Collect only the meetings that loaded successfully AND have a summary
      const loaded = []
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') {
          const m = r.value
          // intelligence is embedded in the meeting object from GET /meetings/{id}
          const summary = m?.intelligence?.summary
          if (summary) {
            loaded.push({
              id:         m.id,
              filename:   m.filename    || 'Untitled Meeting',
              created_at: m.created_at,
              summary,
              topics:     m?.intelligence?.topics       || [],
              decisions:  m?.intelligence?.decisions?.length ?? 0,
              actions:    m?.intelligence?.action_items?.length ?? 0,
            })
          }
        }
      })

      // Sort newest first
      loaded.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setSummaries(loaded)

    } catch (e) {
      setError(e.message || 'Failed to load summaries')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div>
      <PageHeader
        title="Summaries"
        subtitle={loading ? 'Loading...' : `${summaries.length} meeting summary${summaries.length !== 1 ? 'ies' : 'y'}`}
        action={
          !loading && (
            <Button
              variant="ghost"
              size="sm"
              icon={<RefreshCw size={13} />}
              onClick={load}
            >
              Refresh
            </Button>
          )
        }
      />

      {/* Loading state */}
      {loading && (
        <div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            marginBottom: '20px', fontSize: '13px', color: T.text3,
          }}>
            <div className="spinner" style={{ width: 14, height: 14, borderColor: T.accent + '44', borderTopColor: T.accent }} />
            {loadingMsg}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[1,2,3].map(i => <SummaryCardSkeleton key={i} T={T} />)}
          </div>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div style={{
          padding: '20px 24px',
          background: T.dangerBg || 'rgba(239,68,68,0.08)',
          border: `1px solid ${T.danger}33`,
          borderRadius: '14px',
          display: 'flex', alignItems: 'flex-start', gap: '14px',
          marginBottom: '20px',
        }}>
          <AlertCircle size={18} color={T.danger} style={{ flexShrink: 0, marginTop: '1px' }} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: T.danger, marginBottom: '4px' }}>
              Failed to load summaries
            </div>
            <div style={{ fontSize: '13px', color: T.text3, marginBottom: '12px' }}>{error}</div>
            <Button size="sm" onClick={load}>Try again</Button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && summaries.length === 0 && (
        <EmptyState
          icon="📋"
          title="No summaries yet"
          subtitle="Upload and process a meeting to see AI-generated summaries here."
          action={
            <Button onClick={() => navigate('/app/upload')}>
              Upload a Meeting
            </Button>
          }
        />
      )}

      {/* Summary cards */}
      {!loading && !error && summaries.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {summaries.map((s, i) => (
            <div
              key={s.id}
              className="anim-fade-up"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <Card hoverable onClick={() => navigate(`/app/meetings/${s.id}`)}>

                {/* Header: icon + title + date + arrow */}
                <div style={{
                  display: 'flex', alignItems: 'flex-start',
                  justifyContent: 'space-between', gap: '16px',
                  marginBottom: '14px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                    <div style={{
                      width: '36px', height: '36px', borderRadius: '9px',
                      background: T.blueBg, flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <FileText size={17} color={T.blueText} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{
                        fontSize: '15px', fontWeight: 700,
                        color: T.text, letterSpacing: '-0.02em',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {s.filename}
                      </div>
                      <div style={{ fontSize: '12px', color: T.text3, marginTop: '2px' }}>
                        {fmt(s.created_at)}
                      </div>
                    </div>
                  </div>
                  <ArrowRight size={16} color={T.text4} style={{ flexShrink: 0, marginTop: '6px' }} />
                </div>

                {/* Summary text */}
                <p style={{
                  fontSize: '14.5px', fontWeight: 400,
                  color: T.text2, lineHeight: 1.8,
                  margin: '0 0 14px',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}>
                  {s.summary}
                </p>

                {/* Footer: topics + stats */}
                <div style={{
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px',
                }}>
                  {/* Topic pills */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {s.topics.slice(0, 4).map((t, j) => (
                      <span key={j} style={{
                        padding: '3px 10px', borderRadius: '99px',
                        fontSize: '11.5px', fontWeight: 600,
                        color: T.cyanText, background: T.cyanBg,
                      }}>
                        {t.title}
                      </span>
                    ))}
                    {s.topics.length > 4 && (
                      <span style={{
                        padding: '3px 10px', borderRadius: '99px',
                        fontSize: '11.5px', fontWeight: 600,
                        color: T.text3, background: T.surface2,
                      }}>
                        +{s.topics.length - 4} more
                      </span>
                    )}
                  </div>

                  {/* Counts */}
                  <div style={{ display: 'flex', gap: '14px', flexShrink: 0 }}>
                    {s.decisions > 0 && (
                      <span style={{ fontSize: '12px', color: T.purpleText, fontWeight: 600 }}>
                        ⚡ {s.decisions} decision{s.decisions !== 1 ? 's' : ''}
                      </span>
                    )}
                    {s.actions > 0 && (
                      <span style={{ fontSize: '12px', color: T.orangeText, fontWeight: 600 }}>
                        ✅ {s.actions} action{s.actions !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}