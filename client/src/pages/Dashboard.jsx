// client/src/pages/Dashboard.jsx
// Phase 3 upgrade:
//   - Uses StatCard from ui.jsx (count-up animation)
//   - Toast system replaces inline reindexMsg state
//   - page-enter class for smooth page transition
//   - getMeetings now returns { items } not plain array
//   - Mesh gradient hero banner
//   - Activity ring (SVG donut — meetings this week)
//   - Micro-interaction polish throughout

import { getMeetings, getStats, reindexAll, vacuumOrphanedChunks } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Upload, Mic, Zap,
  CheckSquare, FileText, BarChart2,
  Search, RefreshCw, Clock, Activity,
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { StatCard, Card, EmptyState, Skeleton } from '../components/ui'
import OnboardingChecklist from '../components/OnboardingChecklist'
import { useResponsiveGrid } from '../hooks/useResponsiveGrid'
import { useToast } from '../components/Toast'

// ── Helpers ───────────────────────────────────────────────────────────────────

function getGreeting(name = 'there') {
  const h = new Date().getHours()
  const first = name.split(' ')[0]
  if (h >= 5  && h < 12) return { eyebrow: 'Good Morning',   emoji: '☀️',  title: `Rise and align, ${first}.`,        sub: 'Your meetings are summarised and waiting. Start sharp.' }
  if (h >= 12 && h < 14) return { eyebrow: 'Good Afternoon', emoji: '⚡',  title: `Peak hours, ${first}.`,            sub: 'Best time to make decisions. Your insights are ready.' }
  if (h >= 14 && h < 17) return { eyebrow: 'Mid-Afternoon',  emoji: '🎯',  title: `Stay on target, ${first}.`,        sub: "Three hours left in the workday. Here's what your meetings surfaced." }
  if (h >= 17 && h < 20) return { eyebrow: 'Good Evening',   emoji: '🌆',  title: `Wind down with clarity, ${first}.`, sub: 'Close the loop on today — action items and follow-ups are here.' }
  if (h >= 20 && h < 24) return { eyebrow: 'Late Night',     emoji: '🌙',  title: `Still at it, ${first}?`,           sub: "Summly's got you covered. Everything from today is organised." }
  return                          { eyebrow: 'Burning Midnight Oil', emoji: '🔥', title: `The grind is real, ${first}.`, sub: 'Whatever brought you here — your meeting intelligence is ready.' }
}

function timeAgo(iso) {
  if (!iso) return ''
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch { return '' }
}

// ── Activity Ring ─────────────────────────────────────────────────────────────
// Small SVG donut showing how many meetings this week vs total.
// Teaching point: SVG circles use stroke-dashoffset to draw partial arcs.
function ActivityRing({ meetings }) {
  const { T } = useTheme()
  const size = 56, stroke = 5
  const radius = (size - stroke) / 2
  const circ   = 2 * Math.PI * radius

  // Count meetings from last 7 days
  const thisWeek = meetings.filter(m => {
    if (!m.created_at) return false
    return (Date.now() - new Date(m.created_at).getTime()) < 7 * 86400 * 1000
  }).length

  const pct    = meetings.length ? Math.min(thisWeek / Math.max(meetings.length, 1), 1) : 0
  const offset = circ - pct * circ

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={radius}
          fill="none" stroke={T.border} strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={radius}
          fill="none" stroke={T.accent} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0,0,0.2,1)', filter: `drop-shadow(0 0 4px ${T.accent}80)` }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ fontSize: '13px', fontWeight: 800, color: T.accentLight, lineHeight: 1 }}>{thisWeek}</div>
        <div style={{ fontSize: '8px', color: T.text3, fontWeight: 600, marginTop: '1px' }}>week</div>
      </div>
    </div>
  )
}

// ── Meeting Row ───────────────────────────────────────────────────────────────
// Was ['#6366f1','#a855f7', ...] — led with indigo/violet. Swapped for a set
// that avoids that palette entirely while still giving 7 distinct hues for
// per-meeting avatar variety.
const HUES = ['#10b981','#f59e0b','#06b6d4','#f97316','#3b82f6','#f43f5e','#14b8a6']

function MeetingRow({ meeting, index, onClick }) {
  const { T, isDark } = useTheme()
  const [hov, setHov] = useState(false)
  const hue = HUES[index % HUES.length]

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
      style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderRadius: '12px',
        background: hov ? (isDark ? `${hue}0d` : `${hue}08`) : 'transparent',
        border: `1px solid ${hov ? hue + '28' : 'transparent'}`,
        cursor: 'pointer',
        transition: 'all 0.15s var(--ease)',
        gap: '16px',
      }}
    >
      {/* Left */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '13px', minWidth: 0 }}>
        <div style={{
          width: 40, height: 40, borderRadius: '11px', flexShrink: 0,
          background: `${hue}18`, border: `1px solid ${hue}28`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'transform var(--speed) var(--ease-spring)',
          transform: hov ? 'scale(1.07)' : 'scale(1)',
        }}>
          <Mic size={15} color={hue} strokeWidth={2.2} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontSize: '14px', fontWeight: 600, color: T.text,
            letterSpacing: '-0.02em',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            maxWidth: '340px',
          }}>
            {meeting.filename || 'Untitled Meeting'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }}>
            <Clock size={10} color={T.text3} />
            <span style={{ fontSize: '11.5px', color: T.text3 }}>{timeAgo(meeting.created_at)}</span>
          </div>
        </div>
      </div>

      {/* Right */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <span style={{
          padding: '3px 10px', borderRadius: '99px',
          fontSize: '10.5px', fontWeight: 700,
          letterSpacing: '0.04em', textTransform: 'uppercase',
          background: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(5,150,105,0.09)',
          color: '#10b981',
          border: '1px solid rgba(16,185,129,0.22)',
        }}>
          Processed
        </span>
        <ArrowRight size={14} color={hue} style={{
          opacity: hov ? 1 : 0,
          transform: hov ? 'translateX(0)' : 'translateX(-6px)',
          transition: 'all 0.18s var(--ease)',
        }} />
      </div>
    </div>
  )
}

// ── Quick Action Card ─────────────────────────────────────────────────────────
function QuickAction({ icon, label, sub, onClick, color, bg }) {
  const { T } = useTheme()
  const [hov, setHov] = useState(false)

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      className="press"
      role="button"
      tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } }}
      style={{
        padding: '20px',
        borderRadius: '16px',
        background: T.surface,
        border: `1px solid ${hov ? color + '32' : T.border}`,
        boxShadow: hov ? `0 8px 28px ${color}22` : T.cardShadow,
        cursor: 'pointer',
        transition: 'all var(--speed) var(--ease)',
        transform: hov ? 'translateY(-3px)' : 'translateY(0)',
      }}
    >
      <div style={{
        width: 40, height: 40, borderRadius: '11px',
        background: bg, border: `1px solid ${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '14px',
        transition: 'transform var(--speed) var(--ease-spring)',
        transform: hov ? 'scale(1.10) rotate(-4deg)' : 'scale(1)',
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: '14px', fontWeight: 700,
        color: hov ? color : T.text,
        letterSpacing: '-0.02em', marginBottom: '4px',
        transition: 'color var(--speed-fast) var(--ease)',
      }}>
        {label}
      </div>
      <div style={{ fontSize: '12px', color: T.text3 }}>{sub}</div>
    </div>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { T, isDark } = useTheme()
  const { user }      = useAuth()
  const navigate      = useNavigate()
  const { toast }     = useToast()
  const greeting      = getGreeting(user?.full_name || 'there')
  const grid          = useResponsiveGrid()

  const [meetings,    setMeetings]    = useState([])
  const [stats,       setStats]       = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [query,       setQuery]       = useState('')
  const [reindexing,  setReindexing]  = useState(false)
  const [vacuuming,   setVacuuming]   = useState(false)
  const [searchFocus, setSearchFocus] = useState(false)

  // FIX: getMeetings now returns { items, has_more, next_cursor }
  // Old code: getMeetings().then(setMeetings)
  // New code: destructure items from the paginated response
  useEffect(() => {
    Promise.all([
      getMeetings({ limit: 20 }).catch(() => ({ items: [] })),
      getStats().catch(() => null),
    ]).then(([m, s]) => {
      setMeetings(m.items || [])
      setStats(s)
    }).finally(() => setLoading(false))
  }, [])

  const filtered = meetings.filter(m =>
    (m.filename || '').toLowerCase().includes(query.toLowerCase())
  )

  const reindexPollRef = useRef(null)

  const handleReindex = async () => {
    setReindexing(true)
    try {
      // POST returns immediately with a job_id — no more long spinner
      const res = await reindexAll()

      // No Redis mode: server returned final result immediately (done: true)
      if (res.done === true) {
        setReindexing(false)
        toast.success(
          'Reindex complete',
          `Indexed ${res.indexed} of ${res.total} meetings.${res.failed?.length ? ` ${res.failed.length} failed.` : ''}`
        )
        return
      }

      if (!res.job_id) {
        // Old API or unexpected response — treat as done
        setReindexing(false)
        toast.success('Reindex complete', `Indexed ${res.indexed ?? '?'} meetings`)
        return
      }

      // Poll /rag/reindex/status?job_id=... every 2 seconds until done
      const { getApiBase, getToken } = await import('../api/client')
      const BASE  = getApiBase()
      const token = getToken()

      reindexPollRef.current = setInterval(async () => {
        try {
          const r = await fetch(`${BASE}/rag/reindex/status?job_id=${res.job_id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })

          // 404 = job expired, 503 = Redis not running — stop polling, show error
          if (r.status === 404 || r.status === 503) {
            clearInterval(reindexPollRef.current)
            setReindexing(false)
            const err = await r.json().catch(() => ({}))
            toast.error('Reindex status unavailable', err.detail || 'Redis may not be running.')
            return
          }

          if (!r.ok) {
            // Other error (500 etc) — stop polling
            clearInterval(reindexPollRef.current)
            setReindexing(false)
            toast.error('Reindex failed', `Server error: HTTP ${r.status}`)
            return
          }

          const data = await r.json()

          if (data.done) {
            clearInterval(reindexPollRef.current)
            setReindexing(false)
            if (data.status === 'error') {
              toast.error('Reindex failed', data.step || 'Unknown error')
            } else {
              toast.success(
                'Reindex complete',
                `Indexed ${data.indexed} of ${data.total} meetings.${data.failed?.length ? ` ${data.failed.length} failed.` : ''}`
              )
            }
          }
        } catch {
          // Network error — keep trying (transient)
        }
      }, 2000)

    } catch (e) {
      toast.error('Reindex failed', e.message || 'Could not connect to the server.')
      setReindexing(false)
    }
  }

  // Cleanup poll on unmount
  useEffect(() => () => { if (reindexPollRef.current) clearInterval(reindexPollRef.current) }, [])

  // FIX: added to let users fix an already-contaminated ChromaDB themselves.
  // If a meeting was ever deleted directly in Supabase (before DELETE
  // /meetings/{id} existed), its transcript chunks are still sitting in
  // the vector index and can surface in chat under a completely different,
  // currently-active meeting. This button removes anything in ChromaDB
  // whose meeting_id no longer exists in Postgres — safe to run any time.
  const handleVacuum = async () => {
    setVacuuming(true)
    try {
      const res = await vacuumOrphanedChunks()
      const parts = []
      if (res.chunks_fixed) parts.push(`repaired ownership on ${res.chunks_fixed} chunk${res.chunks_fixed !== 1 ? 's' : ''}`)
      if (res.orphaned_meeting_ids?.length) parts.push(`removed ${res.chunks_deleted} orphaned chunk${res.chunks_deleted !== 1 ? 's' : ''} from ${res.orphaned_meeting_ids.length} deleted meeting${res.orphaned_meeting_ids.length !== 1 ? 's' : ''}`)
      if (parts.length) {
        toast.success('Cleanup complete', parts.join(' and ') + '.')
      } else {
        toast.success('Nothing to clean up', 'No issues found — everything is in sync.')
      }
    } catch (e) {
      toast.error('Cleanup failed', e.message || 'Could not connect to the server.')
    } finally {
      setVacuuming(false)
    }
  }

  const statCards = [
    { label: 'Meetings',  value: loading ? 0 : (stats?.total_meetings  ?? 0), icon: '🎙️', color: T.accentLight, bg: isDark ? 'rgba(16,185,129,0.14)' : 'rgba(16,185,129,0.09)',  delay: 0     },
    { label: 'Decisions', value: loading ? 0 : (stats?.total_decisions ?? 0), icon: '⚡', color: T.amber, bg: isDark ? 'rgba(240,181,88,0.16)' : 'rgba(184,121,30,0.10)', delay: 0.07  },
    { label: 'Actions',   value: loading ? 0 : (stats?.total_actions   ?? 0), icon: '✅', color: '#fb923c', bg: isDark ? 'rgba(249,115,22,0.14)' : 'rgba(249,115,22,0.09)',  delay: 0.14  },
    { label: 'Topics',    value: loading ? 0 : (stats?.total_topics    ?? 0), icon: '🏷️', color: '#22d3ee', bg: isDark ? 'rgba(6,182,212,0.14)'  : 'rgba(6,182,212,0.09)',   delay: 0.21  },
  ]

  const quickActions = [
    { icon: <Upload size={17} color={T.accentLight} />,     label: 'Upload',     sub: 'Add a new recording',   to: '/app/upload',    color: T.accentLight, bg: isDark ? 'rgba(16,185,129,0.14)'  : 'rgba(16,185,129,0.09)'  },
    { icon: <FileText size={17} color={T.amber} />,   label: 'Summaries',  sub: 'AI-generated insights', to: '/app/summaries', color: T.amber, bg: isDark ? 'rgba(240,181,88,0.16)' : 'rgba(184,121,30,0.10)' },
    { icon: <CheckSquare size={17} color="#fb923c" />,label: 'Tasks',      sub: 'Track action items',    to: '/app/tasks',     color: '#fb923c', bg: isDark ? 'rgba(249,115,22,0.14)'  : 'rgba(249,115,22,0.09)'  },
    { icon: <BarChart2 size={17} color="#22d3ee" />,  label: 'Analytics',  sub: 'Trends & patterns',     to: '/app/analytics', color: '#22d3ee', bg: isDark ? 'rgba(6,182,212,0.14)'   : 'rgba(6,182,212,0.09)'   },
  ]

  return (
    // page-enter: smooth fade+slide entrance on every navigation
    <div className="page-enter">

      {/* ── Hero Greeting ─────────────────────────────────────── */}
      {/* Mesh gradient background creates depth without being loud */}
      <div style={{
        position: 'relative', overflow: 'hidden',
        borderRadius: grid.isMobile ? '16px' : '20px',
        padding: grid.isMobile ? '20px 18px' : '32px 36px',
        marginBottom: grid.isMobile ? '20px' : '32px',
        background: isDark
          ? 'linear-gradient(135deg, rgba(16,185,129,0.06) 0%, rgba(16,185,129,0.02) 100%)'
          : 'linear-gradient(135deg, rgba(5,150,105,0.05) 0%, rgba(5,150,105,0.01) 100%)',
        border: `1px solid ${isDark ? 'rgba(16,185,129,0.12)' : 'rgba(5,150,105,0.10)'}`,
      }}>

        {/* Ambient orbs — decorative, pointer-events:none so they don't block clicks.
            Was indigo/purple, clashing with this panel's own emerald gradient —
            now emerald + amber (the two brand accents) so it reads as one
            coherent surface instead of two different color systems. */}
        <div style={{
          position: 'absolute', top: '-40px', right: '-40px',
          width: '200px', height: '200px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(240,181,88,0.14), transparent 70%)',
          pointerEvents: 'none',
          animation: 'glowPulse 5s ease-in-out infinite',
        }} />
        <div style={{
          position: 'absolute', bottom: '-30px', left: '30%',
          width: '160px', height: '160px', borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(16,185,129,0.12), transparent 70%)',
          pointerEvents: 'none',
          animation: 'glowPulse 7s ease-in-out infinite 1.5s',
        }} />

        {/* Content row.
            FIX: on mobile this now stacks as a single column (text, then
            ring+status, then a full-width 2-up button row) instead of
            trying to fit "ring · Reindex · Upload Meeting" in one line —
            that combination is comfortably 360px+ wide on its own, which
            never fit inside a ~300px-wide card on an actual phone and was
            overflowing the card and, in some cases, the page itself. */}
        <div style={{
          position: 'relative', zIndex: 1,
          display: 'flex',
          flexDirection: grid.isMobile ? 'column' : 'row',
          alignItems: grid.isMobile ? 'stretch' : 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap', gap: grid.isMobile ? '16px' : '24px',
        }}>
          <div style={{ minWidth: 0 }}>
            {/* Eyebrow pill */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '4px 12px', borderRadius: '99px',
              background: isDark ? 'rgba(16,185,129,0.10)' : 'rgba(5,150,105,0.08)',
              border: `1px solid ${isDark ? 'rgba(16,185,129,0.20)' : 'rgba(5,150,105,0.15)'}`,
              marginBottom: '12px',
            }}>
              <Activity size={10} color={T.accentLight} />
              <span style={{ fontSize: '11px', fontWeight: 700, color: T.accentLight, letterSpacing: '0.10em', textTransform: 'uppercase' }}>
                {greeting.eyebrow}
              </span>
              <span style={{ fontSize: '13px' }}>{greeting.emoji}</span>
            </div>

            {/* Main title with gradient on first word */}
            <h1 style={{
              fontSize: grid.isMobile ? '22px' : 'clamp(24px, 3vw, 34px)',
              fontWeight: 800, letterSpacing: '-0.04em',
              color: T.text, lineHeight: 1.15, marginBottom: '8px',
            }}>
              {greeting.title.split(',')[0]}
              {greeting.title.includes(',') && (
                <span style={{ color: T.text }}>{greeting.title.slice(greeting.title.indexOf(','))}</span>
              )}
            </h1>

            <p style={{
              fontSize: grid.isMobile ? '13.5px' : '15px', color: T.text3,
              lineHeight: 1.6, maxWidth: grid.isMobile ? 'none' : '480px',
            }}>
              {greeting.sub}
            </p>
          </div>

          {/* Right: activity ring + buttons.
              Mobile: ring+"This week" sits on its own row (left-aligned),
              and the two buttons share a full-width row below, each
              taking equal width — no fixed widths, nothing can overflow. */}
          <div style={{
            display: 'flex',
            flexDirection: grid.isMobile ? 'column' : 'row',
            alignItems: grid.isMobile ? 'stretch' : 'center',
            gap: grid.isMobile ? '12px' : '16px',
            flexShrink: 0,
            width: grid.isMobile ? '100%' : 'auto',
          }}>
            {/* Activity ring with label */}
            {!loading && meetings.length > 0 && (
              <div style={{
                display: 'flex', flexDirection: grid.isMobile ? 'row' : 'column',
                alignItems: 'center', gap: grid.isMobile ? '10px' : '5px',
              }}>
                <ActivityRing meetings={meetings} />
                <span style={{ fontSize: grid.isMobile ? '12px' : '10px', color: T.text3, fontWeight: 500 }}>
                  {grid.isMobile ? `${meetings.filter(m => m.created_at && (Date.now() - new Date(m.created_at).getTime()) < 7 * 86400 * 1000).length} meetings this week` : 'This week'}
                </span>
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', width: '100%' }}>
              {/* Reindex button */}
              <button
                onClick={handleReindex}
                disabled={reindexing}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px',
                  flex: grid.isMobile ? 1 : '0 0 auto',
                  minWidth: 0,
                  padding: grid.isMobile ? '11px 12px' : '9px 15px', borderRadius: '10px',
                  border: `1px solid ${T.border}`,
                  background: T.surface, color: T.text2,
                  fontSize: '13px', fontWeight: 600,
                  cursor: reindexing ? 'not-allowed' : 'pointer',
                  opacity: reindexing ? 0.6 : 1,
                  transition: 'all var(--speed) var(--ease)',
                  fontFamily: 'inherit', whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => { if (!reindexing) { e.currentTarget.style.borderColor = T.border2; e.currentTarget.style.color = T.text } }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.text2 }}
              >
                <RefreshCw size={13} style={{ animation: reindexing ? 'spin 0.7s linear infinite' : 'none', flexShrink: 0 }} />
                {reindexing ? 'Reindexing…' : 'Reindex'}
              </button>

              {/* Upload CTA */}
              <button
                onClick={() => navigate('/app/upload')}
                className="press"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  flex: grid.isMobile ? 1 : '0 0 auto',
                  minWidth: 0,
                  padding: grid.isMobile ? '11px 14px' : '9px 20px', borderRadius: '10px',
                  border: 'none',
                  background: isDark ? '#10b981' : '#059669',
                  color: '#fff', fontSize: '13.5px', fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 4px 18px rgba(16,185,129,0.28)',
                  transition: 'all var(--speed) var(--ease)',
                  fontFamily: 'inherit', whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 8px 28px rgba(16,185,129,0.38)' }}
                onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 18px rgba(16,185,129,0.28)' }}
              >
                <Upload size={14} style={{ flexShrink: 0 }} />
                Upload Meeting
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* PHASE 2 (B1): Getting started checklist — only shows for new
          users, self-dismisses once they've graduated past it (see
          OnboardingChecklist for the exact conditions). */}
      {!loading && (
        <OnboardingChecklist
          meetingsCount={stats?.total_meetings ?? 0}
          insightsCount={(stats?.total_decisions ?? 0) + (stats?.total_actions ?? 0) + (stats?.total_topics ?? 0)}
          userId={user?.id}
        />
      )}

      {/* ── Stat Cards ───────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: grid.cols4,
        gap: grid.gap,
        marginBottom: '32px',
      }}>
        {statCards.map(s =>
          loading ? (
            <div key={s.label} style={{ height: '148px', borderRadius: '18px', overflow: 'hidden' }}>
              <Skeleton width="100%" height="148px" style={{ borderRadius: '18px' }} />
            </div>
          ) : (
            // FIX: uses StatCard from ui.jsx — has built-in count-up animation
            // Old: local PremiumStatCard had no animation
            <StatCard key={s.label} {...s} />
          )
        )}
      </div>

      {/* ── Recent Meetings ───────────────────────────────────── */}
      <div className="anim-fade-up anim-fade-up-3" style={{ marginBottom: '28px' }}>
        <div style={{
          borderRadius: '20px', background: T.surface,
          border: `1px solid ${T.border}`, boxShadow: T.cardShadow,
          overflow: 'hidden',
        }}>
          {/* Card header */}
          <div style={{
            display: 'flex',
            flexDirection: grid.isMobile ? 'column' : 'row',
            alignItems: grid.isMobile ? 'stretch' : 'center',
            justifyContent: 'space-between',
            padding: grid.isMobile ? '16px 16px' : '20px 24px',
            borderBottom: `1px solid ${T.border}`,
            gap: '14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: 32, height: 32, borderRadius: '9px',
                background: T.accentBg,
                border: `1px solid ${T.accent}40`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Mic size={14} color={T.accent} strokeWidth={2.1} />
              </div>
              <span style={{ fontSize: '16px', fontWeight: 750, color: T.text, letterSpacing: '-0.03em' }}>
                Recent Meetings
              </span>
              {meetings.length > 0 && (
                <span style={{
                  padding: '2px 9px', borderRadius: '99px',
                  fontSize: '11px', fontWeight: 700,
                  background: T.accentBg,
                  color: T.accent, border: `1px solid ${T.accent}38`,
                }}>
                  {meetings.length}
                </span>
              )}
            </div>

            {/* Search + View All — full-width row on mobile, search grows
                to fill remaining space instead of a fixed 180px that could
                overflow a narrow header. */}
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: grid.isMobile ? 1 : '0 0 auto', minWidth: 0 }}>
                <Search size={12} color={searchFocus ? T.accent : T.text3} style={{
                  position: 'absolute', left: '11px', top: '50%',
                  transform: 'translateY(-50%)',
                  transition: 'color var(--speed-fast) var(--ease)',
                  pointerEvents: 'none',
                }} />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onFocus={() => setSearchFocus(true)}
                  onBlur={() => setSearchFocus(false)}
                  placeholder="Filter meetings…"
                  style={{
                    padding: '8px 14px 8px 30px',
                    borderRadius: '10px',
                    width: grid.isMobile ? '100%' : '180px',
                    border: `1px solid ${searchFocus ? T.accent : T.border}`,
                    background: T.inputBg, color: T.text,
                    fontSize: '13px', outline: 'none',
                    transition: 'border-color var(--speed-fast) var(--ease), box-shadow var(--speed-fast) var(--ease)',
                    boxShadow: searchFocus ? `0 0 0 3px ${T.accent}20` : 'none',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <button
                onClick={() => navigate('/app/meetings')}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                  padding: '8px 14px', borderRadius: '10px', flexShrink: 0,
                  border: `1px solid ${T.border}`,
                  background: 'transparent', color: T.text3,
                  fontSize: '12.5px', fontWeight: 600, cursor: 'pointer',
                  transition: 'all var(--speed-fast) var(--ease)',
                  fontFamily: 'inherit', whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => { e.currentTarget.style.color = T.text; e.currentTarget.style.borderColor = T.border2; e.currentTarget.style.background = T.surface2 }}
                onMouseLeave={e => { e.currentTarget.style.color = T.text3; e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = 'transparent' }}
              >
                View all <ArrowRight size={12} />
              </button>
            </div>
          </div>

          {/* List */}
          <div style={{ padding: '10px 8px' }}>
            {loading ? (
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[1,2,3].map(i => (
                  <div key={i} style={{ display: 'flex', gap: '13px', alignItems: 'center', padding: '4px 12px' }}>
                    <Skeleton width="40px" height="40px" style={{ borderRadius: '11px', flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <Skeleton width="52%" height="14px" style={{ marginBottom: '8px' }} />
                      <Skeleton width="25%" height="11px" />
                    </div>
                    <Skeleton width="80px" height="22px" style={{ borderRadius: '99px' }} />
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <EmptyState
                icon={query ? '🔍' : '🎙️'}
                title={query ? `No results for "${query}"` : 'No meetings yet'}
                subtitle={query ? 'Try a different search term.' : 'Upload your first meeting recording to get started.'}
                action={!query && (
                  <button
                    onClick={() => navigate('/app/upload')}
                    className="press"
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: '8px',
                      padding: '10px 22px', borderRadius: '10px',
                      border: 'none',
                      background: isDark ? '#10b981' : '#059669',
                      color: '#fff', fontSize: '13.5px', fontWeight: 700,
                      cursor: 'pointer',
                      boxShadow: '0 4px 16px rgba(16,185,129,0.32)',
                      fontFamily: 'inherit',
                    }}
                  >
                    <Upload size={14} /> Upload Meeting
                  </button>
                )}
              />
            ) : (
              filtered.slice(0, 8).map((m, i) => (
                <MeetingRow
                  key={m.id}
                  meeting={m}
                  index={i}
                  onClick={() => navigate(`/app/meetings/${m.id}`)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Quick Actions ─────────────────────────────────────── */}
      {!loading && meetings.length > 0 && (
        <div className="anim-fade-up anim-fade-up-4">
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            marginBottom: '14px',
          }}>
            <Zap size={13} color={T.accentLight} fill={T.accentLight} />
            <span style={{
              fontSize: '11px', fontWeight: 700,
              letterSpacing: '0.10em', textTransform: 'uppercase',
              color: T.text3,
            }}>
              Quick Actions
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: grid.cols4, gap: grid.gap }}>
            {quickActions.map(q => (
              <QuickAction key={q.label} {...q} onClick={() => navigate(q.to)} />
            ))}
          </div>
        </div>
      )}

    </div>
  )
}