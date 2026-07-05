// client/src/pages/MeetingDetail.jsx
//
// WHAT THIS PAGE DOES:
// ────────────────────
// Shows everything about one meeting in a tabbed layout:
//
//   Summary    — AI executive summary, decisions, topics, key quotes
//   Health     — Meeting health score with animated ring + metric bars
//   Transcript — Full searchable transcript with keyword highlight
//   Speakers   — NEW: diarization view showing who spoke when + talk time
//   Tasks      — Action items with owner, deadline, priority, status
//
// NEW IN THIS VERSION:
// ─────────────────────
// Speakers Tab — shows speaker diarization results from pyannote.audio.
// Your backend already runs diarization, but the frontend had no UI for it.
// This tab shows:
//   - Each speaker's total talk time and % of meeting
//   - A visual timeline of when each speaker was talking
//   - Sentiment per speaker (positive/neutral/negative)
//   - Color-coded speaker labels throughout
//
// FIX: All getMeetingIntelligence calls removed — intel is now
// embedded inside getMeeting() response (intel = meeting.intelligence).
// The old code already did this correctly; this version makes it explicit.

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useParams, useNavigate }  from 'react-router-dom'
import {
  ArrowLeft, FileText, Zap, CheckSquare,
  MessageSquare, Tag, Clock, Copy, Check,
  Download, Link, Mail, Search, X, Heart,
  Users, Play, Pause, RefreshCw, Mic,
  Folder, ChevronDown, Trash2, AlertTriangle,
} from 'lucide-react'
import { useTheme }     from '../ThemeContext'
import {
  Card, Tabs, Badge, ScoreRing,
  ProgressBar, Button, EmptyState, Skeleton,
} from '../components/ui'
import { useResponsiveGrid } from '../hooks/useResponsiveGrid'
import { useToast }          from '../components/Toast'
import { useWorkspace }      from '../context/WorkspaceContext'
import {
  getMeeting, getMeetingHealth, getMeetingQuotes,
  getMeetingAITitle, exportMeetingPDF, getFollowupEmail,
  getDiarization, runDiarization,
  getMeetingSentiment, runSentimentAnalysis,
  getMeetingWorkspace, addMeetingToWorkspace, removeMeetingFromWorkspace,
  deleteMeeting,
} from '../api/client'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso.slice(0, 16) }
}

// ── Workspace assignment control ─────────────────────────────────────────────
// FIX: Before this, a meeting could never actually end up inside a workspace
// through the UI — Workspaces.jsx could list/create/delete workspaces, but
// there was no "add this meeting to a workspace" action anywhere. Workspace
// detail pages permanently showed "No meetings yet" even after creating one.
//
// This button shows the meeting's current workspace (if any, via the new
// GET /meetings/{id}/workspace endpoint) and opens a small menu to move it
// into a different workspace, or take it out entirely.
function WorkspaceAssign({ meetingId, T }) {
  const { workspaces } = useWorkspace() || {}
  const { toast } = useToast()

  const [current, setCurrent] = useState(null) // { id, name, type, color } | null
  const [loading, setLoading] = useState(true)
  const [open,    setOpen]    = useState(false)
  const [saving,  setSaving]  = useState(false)

  useEffect(() => {
    let cancelled = false
    getMeetingWorkspace(meetingId)
      .then(res => { if (!cancelled) setCurrent(res?.workspace || null) })
      .catch(() => { if (!cancelled) setCurrent(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [meetingId])

  async function handleAssign(ws) {
    setOpen(false)
    if (ws && current && ws.id === current.id) return // no-op, already here
    setSaving(true)
    try {
      // Meetings can only belong to one workspace in this UI — moving means
      // removing from the old one (if any) before adding to the new one.
      if (current) await removeMeetingFromWorkspace(current.id, meetingId)
      if (ws) {
        await addMeetingToWorkspace(ws.id, meetingId)
        setCurrent(ws)
        toast.success('Added to workspace', `Moved to "${ws.name}".`)
      } else {
        setCurrent(null)
        toast.success('Removed from workspace', 'This meeting is no longer in a workspace.')
      }
    } catch (e) {
      toast.error('Could not update workspace', e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ position: 'relative' }}>
      <Button
        variant="ghost" size="sm"
        icon={<Folder size={13} color={current?.color || undefined} />}
        onClick={() => setOpen(v => !v)}
        loading={saving}
      >
        {loading ? 'Workspace' : (current ? current.name : 'Add to Workspace')}
        {!loading && <ChevronDown size={12} style={{ marginLeft: '-2px' }} />}
      </Button>

      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 200 }} />
          <div
            className="anim-fade-down"
            style={{
              position: 'absolute', top: 'calc(100% + 6px)', right: 0, minWidth: '230px',
              background: T.surface, border: `1px solid ${T.border}`, borderRadius: '10px',
              boxShadow: '0 14px 34px rgba(0,0,0,0.28)', zIndex: 201, overflow: 'hidden',
            }}
          >
            <div style={{ maxHeight: '220px', overflowY: 'auto' }}>
              {(!workspaces || workspaces.length === 0) ? (
                <div style={{ padding: '14px', fontSize: '12.5px', color: T.text3, lineHeight: 1.5 }}>
                  No workspaces yet. Create one from the Workspaces page first.
                </div>
              ) : workspaces.map(ws => (
                <button
                  key={ws.id}
                  onClick={() => handleAssign(ws)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '10px 14px', background: 'none', border: 'none',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = T.surface2}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: ws.color || '#10b981', flexShrink: 0 }} />
                  <span style={{
                    flex: 1, fontSize: '13px', fontWeight: 600, color: T.text,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {ws.name}
                  </span>
                  {current?.id === ws.id && <Check size={13} color={T.accent} />}
                </button>
              ))}
            </div>
            {current && (
              <>
                <div style={{ height: 1, background: T.border }} />
                <button
                  onClick={() => handleAssign(null)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                    padding: '10px 14px', background: 'none', border: 'none',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                    fontSize: '12.5px', fontWeight: 600, color: T.danger,
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = `${T.danger}10`}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  <X size={13} /> Remove from workspace
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function fmtSeconds(sec) {
  if (!sec) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function priorityColor(p, T) {
  if (p === 'high') return { color: T.danger  || '#ef4444', bg: T.dangerBg  || '#fee2e2' }
  if (p === 'low')  return { color: T.emerald,               bg: T.emeraldBg }
  return                    { color: T.warning || '#f59e0b', bg: T.warningBg || '#fef3c7' }
}

// Highlight matching text — returns React elements with highlighted spans
function Highlighted({ text = '', query = '' }) {
  const { T, isDark } = useTheme()
  if (!query.trim()) return <span>{text}</span>
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex   = new RegExp(`(${escaped})`, 'gi')
  const parts   = text.split(regex)
  return (
    <span>
      {parts.map((part, i) =>
        regex.test(part)
          ? <mark key={i} style={{
              background: isDark ? 'rgba(234,179,8,0.35)' : 'rgba(234,179,8,0.42)',
              color: T.text, borderRadius: '3px', padding: '0 2px',
            }}>{part}</mark>
          : <span key={i}>{part}</span>
      )}
    </span>
  )
}

function downloadTXT(meeting, intel) {
  const lines = [
    'MEETING REPORT', '═══════════════════════════════════════',
    `File: ${meeting.filename || 'Untitled'}`,
    `Date: ${fmt(meeting.created_at)}`, '',
    'SUMMARY', '───────────────────────────────────────',
    intel?.summary || 'No summary.', '',
  ]
  if (intel?.decisions?.length) {
    lines.push('DECISIONS', '───────────────────────────────────────')
    intel.decisions.forEach((d, i) => {
      lines.push(`${i+1}. ${d.decision}`)
      if (d.rationale) lines.push(`   ↳ ${d.rationale}`)
    })
    lines.push('')
  }
  if (intel?.action_items?.length) {
    lines.push('ACTION ITEMS', '───────────────────────────────────────')
    intel.action_items.forEach((item, i) => {
      lines.push(`${i+1}. ${item.task}`)
      if (item.owner)    lines.push(`   Owner: ${item.owner}`)
      if (item.deadline) lines.push(`   Deadline: ${item.deadline}`)
    })
    lines.push('')
  }
  lines.push('TRANSCRIPT', '───────────────────────────────────────', meeting.transcript || '')
  const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
  const url  = URL.createObjectURL(blob)
  const a    = Object.assign(document.createElement('a'), {
    href: url,
    download: `${meeting.filename || 'meeting'}_report.txt`,
  })
  a.click()
  URL.revokeObjectURL(url)
}

function CopyBtn({ text, label = 'Copy' }) {
  const { T } = useTheme()
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '5px',
        padding: '5px 11px', borderRadius: '7px',
        fontSize: '12px', fontWeight: 600,
        color:       copied ? T.emerald : T.text3,
        background:  copied ? T.emeraldBg : T.surface2,
        border:      `1px solid ${copied ? T.emerald + '44' : T.border}`,
        cursor: 'pointer', transition: 'all 0.15s ease',
        fontFamily: 'inherit',
      }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

// ── Tab: Summary ──────────────────────────────────────────────────────────────
function SummaryTab({ intel, quotes, aiTitle, T, grid }) {
  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {aiTitle && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: '7px 14px', borderRadius: '99px',
          background: T.accentBg, border: `1px solid ${T.accent}33`,
          width: 'fit-content',
        }}>
          <span>✨</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: T.accentLight }}>
            AI Title: {aiTitle}
          </span>
        </div>
      )}

      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
          <div style={{ width: 34, height: 34, borderRadius: '9px', background: T.blueBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <FileText size={16} color={T.blueText} />
          </div>
          <span style={{ fontSize: '16px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
            Summary
          </span>
        </div>
        <p style={{ fontSize: '15.5px', color: T.text2, lineHeight: 1.85, margin: 0 }}>
          {intel?.summary || 'No summary available. The meeting may still be processing.'}
        </p>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: grid?.cols2 || '1fr 1fr', gap: '20px' }}>
        {/* Decisions */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: 32, height: 32, borderRadius: '8px', background: T.purpleBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Zap size={15} color={T.purpleText} />
              </div>
              <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Decisions</span>
            </div>
            <span style={{ padding: '2px 9px', borderRadius: '99px', fontSize: '11px', fontWeight: 700, color: T.purpleText, background: T.purpleBg }}>
              {intel?.decisions?.length || 0}
            </span>
          </div>
          {intel?.decisions?.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {intel.decisions.map((d, i) => (
                <div key={i} style={{ padding: '13px 15px', borderRadius: '10px', background: T.purpleBg, border: `1px solid ${T.purple}22` }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: T.text, lineHeight: 1.55, marginBottom: d.rationale ? '6px' : 0 }}>
                    {d.decision}
                  </div>
                  {d.rationale && (
                    <div style={{ fontSize: '12.5px', color: T.text3, fontStyle: 'italic', lineHeight: 1.5 }}>
                      ↳ {d.rationale}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: T.text3 }}>No decisions recorded.</div>
          )}
        </Card>

        {/* Topics */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: 32, height: 32, borderRadius: '8px', background: T.cyanBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Tag size={15} color={T.cyanText} />
              </div>
              <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Topics</span>
            </div>
            <span style={{ padding: '2px 9px', borderRadius: '99px', fontSize: '11px', fontWeight: 700, color: T.cyanText, background: T.cyanBg }}>
              {intel?.topics?.length || 0}
            </span>
          </div>
          {intel?.topics?.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {intel.topics.map((t, i) => (
                <div key={i} style={{ padding: '10px 13px', borderRadius: '9px', background: T.cyanBg, border: `1px solid ${T.cyan || T.cyanText}22` }}>
                  <div style={{ fontSize: '13px', fontWeight: 650, color: T.cyanText, marginBottom: t.description ? '3px' : 0 }}>
                    {t.title}
                  </div>
                  {t.description && (
                    <div style={{ fontSize: '12px', color: T.text3, lineHeight: 1.5 }}>{t.description}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '13px', color: T.text3 }}>No topics identified.</div>
          )}
        </Card>
      </div>

      {/* Key Quotes */}
      {quotes.length > 0 && (
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <span style={{ fontSize: '20px' }}>💬</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Key Quotes</span>
            <span style={{ padding: '2px 9px', borderRadius: '99px', fontSize: '11px', fontWeight: 700, color: T.cyanText, background: T.cyanBg }}>{quotes.length}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {quotes.map((q, i) => (
              <div key={i} style={{
                padding: '14px 16px', borderRadius: '10px',
                background: T.surface2, border: `1px solid ${T.border}`,
                borderLeft: `3px solid ${T.accent}`,
              }}>
                <div style={{ fontSize: '14px', fontWeight: 500, color: T.text, lineHeight: 1.6, fontStyle: 'italic', marginBottom: q.speaker ? '7px' : 0 }}>
                  "{q.quote}"
                </div>
                {q.speaker && (
                  <span style={{ fontSize: '12px', fontWeight: 650, color: T.accentLight }}>— {q.speaker}</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Tab: Health ───────────────────────────────────────────────────────────────
function HealthTab({ health, T }) {
  if (!health) return (
    <div className="page-enter">
      <EmptyState icon="❤️" title="No health data" subtitle="Health analysis was not available for this meeting." />
    </div>
  )

  const metrics = [
    { label: 'Participation',    value: health.participation,    color: '#3b82f6' },
    { label: 'Decision Quality', value: health.decision_quality, color: '#f59e0b' },
    { label: 'Action Clarity',   value: health.action_clarity,   color: '#f97316' },
    { label: 'Follow-up Risk',   value: health.followup_risk,    color: '#10b981' },
  ]

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <Card>
        <div style={{ display: 'flex', gap: '40px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
            <ScoreRing score={health.overall_score} size={140} strokeWidth={12} label="/ 100" />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: T.text }}>Overall Score</div>
              <div style={{ fontSize: '12px', color: T.text3, marginTop: '3px' }}>
                {health.overall_score >= 80 ? '🌟 Excellent' : health.overall_score >= 60 ? '👍 Good' : '⚠️ Needs work'}
              </div>
            </div>
          </div>
          <div style={{ flex: 1, minWidth: '240px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {metrics.map(m => (
              <div key={m.label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '7px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: T.text2 }}>{m.label}</span>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: m.color }}>{m.value}</span>
                </div>
                <ProgressBar value={m.value} max={100} color={m.color} height={7} />
              </div>
            ))}
          </div>
        </div>
        {(health.highlights || health.concerns) && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginTop: '24px' }}>
            {health.highlights && (
              <div style={{ padding: '14px 16px', borderRadius: '12px', background: T.emeraldBg, border: `1px solid ${T.emerald}22` }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: T.emerald, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>✓ Highlights</div>
                <div style={{ fontSize: '13px', color: T.text2, lineHeight: 1.6 }}>{health.highlights}</div>
              </div>
            )}
            {health.concerns && (
              <div style={{ padding: '14px 16px', borderRadius: '12px', background: T.warningBg || '#fef3c7', border: `1px solid ${T.warning || '#f59e0b'}22` }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: T.warning || '#f59e0b', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>⚠ To Improve</div>
                <div style={{ fontSize: '13px', color: T.text2, lineHeight: 1.6 }}>{health.concerns}</div>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}

// ── Tab: Transcript ───────────────────────────────────────────────────────────
function TranscriptTab({ transcript, T }) {
  const [query,  setQuery]  = useState('')
  const [focus,  setFocus]  = useState(false)

  const matchCount = useMemo(() => {
    if (!query.trim() || !transcript) return 0
    const regex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
    return (transcript.match(regex) || []).length
  }, [query, transcript])

  return (
    <div className="page-enter">
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px', borderBottom: `1px solid ${T.border}`,
          flexWrap: 'wrap', gap: '10px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={16} color={T.text3} />
            <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Transcript</span>
            {transcript && (
              <span style={{ fontSize: '11px', color: T.text3, fontWeight: 500 }}>
                {transcript.split(' ').length.toLocaleString()} words
              </span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={12} color={focus ? T.accent : T.text3} style={{
                position: 'absolute', left: '10px', top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none',
              }} />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onFocus={() => setFocus(true)}
                onBlur={()  => setFocus(false)}
                placeholder="Search transcript…"
                style={{
                  padding: '7px 28px 7px 28px', borderRadius: '8px',
                  width: '200px',
                  border: `1px solid ${focus ? T.accent : T.border}`,
                  background: T.inputBg || T.surface2, color: T.text,
                  fontSize: '12.5px', outline: 'none',
                  boxShadow: focus ? `0 0 0 3px ${T.accent}18` : 'none',
                  transition: 'all 0.15s ease', fontFamily: 'inherit',
                }}
              />
              {query && (
                <button onClick={() => setQuery('')} style={{
                  position: 'absolute', right: '8px', top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: T.text3, padding: '2px', display: 'flex',
                }}>
                  <X size={11} />
                </button>
              )}
            </div>
            {query && (
              <span style={{ fontSize: '11.5px', color: matchCount > 0 ? T.emerald : T.text3, fontWeight: 600 }}>
                {matchCount > 0 ? `${matchCount} match${matchCount !== 1 ? 'es' : ''}` : 'No matches'}
              </span>
            )}
            <CopyBtn text={transcript || ''} />
          </div>
        </div>
        <div style={{
          padding: '24px', fontSize: '14.5px', color: T.text2,
          lineHeight: 1.9, letterSpacing: '-0.005em',
          maxHeight: '600px', overflowY: 'auto',
        }}>
          {transcript
            ? <Highlighted text={transcript} query={query} />
            : <span style={{ color: T.text3 }}>No transcript available.</span>
          }
        </div>
      </Card>
    </div>
  )
}

// ── Tab: Speakers (DIARIZATION) ───────────────────────────────────────────────
//
// WHAT IS DIARIZATION?
// "Speaker diarization" = splitting a recording into segments and labeling
// each segment with the speaker who said it. Think of subtitles that say
// "[Speaker 1]: We need to ship by Friday."
//
// Your backend uses pyannote.audio — a deep learning model that analyzes
// audio waveforms to detect voice changes. It returns:
//   segments: [{ speaker, start, end, text }, ...]
//   speakers: [{ id, total_time, percentage }, ...]
//
// This tab fetches that data and shows:
//   1. Per-speaker stats (talk time, % of meeting, color-coded)
//   2. A visual timeline bar showing when each speaker was active
//   3. The segmented transcript with color-coded speaker labels
//
// SPEAKER COLORS:
// We assign one of 8 distinct colors to each speaker by index.
// The same speaker always gets the same color on this page.
// Was led by indigo/purple — reordered to lead with emerald and dropped
// indigo/violet from the rotation entirely, replaced with teal/rose.

const SPEAKER_COLORS = [
  '#10b981', // emerald
  '#f59e0b', // amber
  '#3b82f6', // blue
  '#f97316', // orange
  '#06b6d4', // cyan
  '#ef4444', // red
  '#f43f5e', // rose
  '#14b8a6', // teal
]

function SpeakersTab({ meetingId, T }) {
  const [diarization, setDiarization]   = useState(null)
  const [sentiment,   setSentiment]     = useState(null)
  const [loading,     setLoading]       = useState(true)
  const [running,     setRunning]       = useState(false)
  const [error,       setError]         = useState(null)
  const { toast }                       = useToast()

  // Load diarization data when tab is opened
  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [diarRes, sentRes] = await Promise.allSettled([
          getDiarization(meetingId),
          getMeetingSentiment(meetingId),
        ])
        if (diarRes.status === 'fulfilled') setDiarization(diarRes.value)
        if (sentRes.status === 'fulfilled') setSentiment(sentRes.value)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [meetingId])

  // Run diarization — POST to backend, polls until complete
  async function handleRunDiarization() {
    setRunning(true)
    setError(null)
    try {
      toast.info('Running speaker detection', 'This takes 30-60 seconds for a typical meeting.')
      const result = await runDiarization(meetingId)
      setDiarization(result)
      toast.success('Speaker detection complete', `Found ${result?.speakers?.length || 0} speakers.`)

      // Also run sentiment after diarization succeeds
      try {
        const sentResult = await runSentimentAnalysis(meetingId)
        setSentiment(sentResult)
      } catch {
        // sentiment failure is non-fatal
      }
    } catch (e) {
      setError(e.message)
      toast.error('Speaker detection failed', e.message)
    } finally {
      setRunning(false)
    }
  }

  // Assign a consistent color to each speaker by their index
  const speakerColor = useCallback((speakerId) => {
    const speakers = diarization?.speakers || []
    const idx      = speakers.findIndex(s => s.id === speakerId)
    return SPEAKER_COLORS[idx % SPEAKER_COLORS.length]
  }, [diarization])

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {[1,2,3].map(i => (
        <Card key={i}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Skeleton width="40px" height="40px" style={{ borderRadius: '50%' }} />
            <div style={{ flex: 1 }}>
              <Skeleton width="30%" height="14px" style={{ marginBottom: '8px' }} />
              <Skeleton width="60%" height="10px" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  )

  // ── Not yet run ─────────────────────────────────────────────────────────────
  if (!diarization || !diarization.speakers?.length) return (
    <div className="page-enter">
      <EmptyState
        icon={<Mic size={40} color={T.text4} />}
        title="Speaker detection not run"
        subtitle="Run speaker diarization to see who spoke when, talk time per speaker, and per-speaker sentiment."
        action={
          <Button
            onClick={handleRunDiarization}
            loading={running}
            icon={<Play size={14} />}
          >
            {running ? 'Running (30-60s)...' : 'Run Speaker Detection'}
          </Button>
        }
      />
      {error && (
        <div style={{
          marginTop: '16px', padding: '14px 18px',
          background: T.dangerBg || 'rgba(239,68,68,0.08)',
          border: `1px solid ${T.danger || '#ef4444'}33`,
          borderRadius: '12px', fontSize: '13px', color: T.danger || '#ef4444',
        }}>
          {error}
        </div>
      )}
    </div>
  )

  const { speakers, segments, total_duration } = diarization
  const totalSecs = total_duration || segments[segments.length - 1]?.end || 1

  return (
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Re-run button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="ghost"
          size="sm"
          icon={<RefreshCw size={12} />}
          onClick={handleRunDiarization}
          loading={running}
        >
          Re-analyse
        </Button>
      </div>

      {/* ── Speaker summary cards ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${Math.min(speakers.length, 3)}, 1fr)`,
        gap: '14px',
      }}>
        {speakers.map((sp, i) => {
          const color   = speakerColor(sp.id)
          const sentObj = sentiment?.speakers?.find(s => s.id === sp.id)
          return (
            <Card key={sp.id} style={{ borderTop: `3px solid ${color}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                {/* Speaker avatar circle */}
                <div style={{
                  width: '38px', height: '38px', borderRadius: '50%',
                  background: `${color}22`,
                  border: `2px solid ${color}55`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '14px', fontWeight: 800, color,
                  flexShrink: 0,
                }}>
                  {sp.label ? sp.label[0].toUpperCase() : `S${i+1}`}
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: T.text }}>
                    {sp.label || `Speaker ${i+1}`}
                  </div>
                  <div style={{ fontSize: '11px', color: T.text3 }}>
                    {fmtSeconds(sp.total_time)} total
                  </div>
                </div>
              </div>

              {/* Talk time bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                  <span style={{ fontSize: '11.5px', color: T.text3 }}>Talk time</span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color }}>
                    {sp.percentage?.toFixed(0) || 0}%
                  </span>
                </div>
                <div style={{ height: '5px', borderRadius: '99px', background: T.surface2, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${sp.percentage || 0}%`,
                    background: color,
                    borderRadius: '99px',
                    transition: 'width 0.8s ease',
                  }} />
                </div>
              </div>

              {/* Sentiment badge if available */}
              {sentObj && (
                <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '11px', color: T.text3 }}>Sentiment</span>
                  <span style={{
                    padding: '2px 8px', borderRadius: '99px',
                    fontSize: '11px', fontWeight: 700,
                    color:      sentObj.sentiment === 'positive' ? T.emerald : sentObj.sentiment === 'negative' ? T.danger || '#ef4444' : T.text3,
                    background: sentObj.sentiment === 'positive' ? T.emeraldBg : sentObj.sentiment === 'negative' ? (T.dangerBg || '#fee2e2') : T.surface2,
                  }}>
                    {sentObj.sentiment === 'positive' ? '😊 Positive' : sentObj.sentiment === 'negative' ? '😟 Negative' : '😐 Neutral'}
                  </span>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {/* ── Visual timeline ── */}
      <Card>
        <div style={{ fontSize: '14px', fontWeight: 700, color: T.text, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={15} color={T.text3} />
          Speaking Timeline
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          {speakers.map((sp, i) => (
            <div key={sp.id} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '3px', background: speakerColor(sp.id), flexShrink: 0 }} />
              <span style={{ fontSize: '12px', color: T.text3, fontWeight: 500 }}>
                {sp.label || `Speaker ${i+1}`}
              </span>
            </div>
          ))}
        </div>

        {/* Timeline bar */}
        <div style={{
          height: '28px',
          borderRadius: '6px',
          background: T.surface2,
          overflow: 'hidden',
          position: 'relative',
        }}>
          {segments.map((seg, i) => {
            const left  = ((seg.start / totalSecs) * 100).toFixed(2)
            const width = (((seg.end - seg.start) / totalSecs) * 100).toFixed(2)
            const color = speakerColor(seg.speaker)
            return (
              <div
                key={i}
                title={`${seg.speaker}: ${fmtSeconds(seg.start)} – ${fmtSeconds(seg.end)}`}
                style={{
                  position: 'absolute',
                  top: '2px', bottom: '2px',
                  left:  `${left}%`,
                  width: `${width}%`,
                  minWidth: '2px',
                  background: color,
                  borderRadius: '3px',
                  opacity: 0.85,
                }}
              />
            )
          })}
        </div>

        {/* Time labels */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontFamily: 'var(--font-mono, monospace)' }}>
          <span style={{ fontSize: '10.5px', color: T.text4 }}>0:00</span>
          <span style={{ fontSize: '10.5px', color: T.text4 }}>{fmtSeconds(totalSecs / 2)}</span>
          <span style={{ fontSize: '10.5px', color: T.text4 }}>{fmtSeconds(totalSecs)}</span>
        </div>
      </Card>

      {/* ── Segmented transcript ── */}
      {segments?.length > 0 && (
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={15} color={T.text3} />
            <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Speaker Transcript</span>
          </div>
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {segments.map((seg, i) => {
              const color = speakerColor(seg.speaker)
              return (
                <div key={i} style={{
                  display: 'flex', gap: '14px',
                  padding: '12px 20px',
                  borderBottom: i < segments.length - 1 ? `1px solid ${T.border}` : 'none',
                }}>
                  {/* Speaker label */}
                  <div style={{ flexShrink: 0, width: '80px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color }}>
                      {seg.speaker_label || seg.speaker}
                    </div>
                    {/* Mono face for the timestamp — matches the guide's
                        transcript timestamp-gutter spec, and ties this back
                        to the meeting-ID/date metadata elsewhere using the
                        same face. */}
                    <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '10px', color: T.text4, marginTop: '2px' }}>
                      {fmtSeconds(seg.start)}
                    </div>
                  </div>

                  {/* Segment text */}
                  <div style={{ flex: 1, fontSize: '13.5px', color: T.text2, lineHeight: 1.7 }}>
                    {seg.text || '(silence)'}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Tab: Tasks ────────────────────────────────────────────────────────────────
function TasksTab({ intel, T }) {
  const items = intel?.action_items || []

  return (
    <div className="page-enter">
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '18px 22px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <CheckSquare size={16} color={T.orangeText} />
          <span style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Action Items</span>
          <span style={{ padding: '2px 9px', borderRadius: '99px', fontSize: '11px', fontWeight: 700, color: T.orangeText, background: T.orangeBg }}>
            {items.length}
          </span>
        </div>
        {items.length === 0 ? (
          <EmptyState icon="✅" title="No action items" subtitle="No action items were found in this meeting." />
        ) : (
          <div>
            {items.map((item, i) => {
              const pc = priorityColor(item.priority, T)
              return (
                <div
                  key={i}
                  className="anim-fade-up"
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  <div
                    style={{
                      display: 'flex', alignItems: 'flex-start',
                      justifyContent: 'space-between', gap: '16px',
                      padding: '16px 22px',
                      borderBottom: i < items.length - 1 ? `1px solid ${T.border}` : 'none',
                      transition: 'background 0.12s ease',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = T.surfaceHover || T.surface2}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: T.text, lineHeight: 1.55, marginBottom: '6px' }}>
                        {item.task}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '12px', color: T.text3 }}>
                        {item.owner    && <span>👤 {item.owner}</span>}
                        {item.deadline && <span>📅 {item.deadline}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                      <Badge color={pc.color} bg={pc.bg}>{item.priority || 'medium'}</Badge>
                      <Badge
                        color={item.status === 'done' ? T.emerald : T.warning || '#f59e0b'}
                        bg={item.status === 'done' ? T.emeraldBg : T.warningBg || '#fef3c7'}
                      >
                        {item.status || 'open'}
                      </Badge>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function MeetingDetail() {
  const { T }    = useTheme()
  const { id }   = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const grid     = useResponsiveGrid()

  const [meeting,      setMeeting]      = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState(null)
  const [health,       setHealth]       = useState(null)
  const [quotes,       setQuotes]       = useState([])
  const [aiTitle,      setAiTitle]      = useState(null)
  const [activeTab,    setActiveTab]    = useState('summary')
  const [linkCopied,   setLinkCopied]   = useState(false)
  const [pdfLoading,   setPdfLoading]   = useState(false)
  const [emailModal,   setEmailModal]   = useState(false)
  const [emailContent, setEmailContent] = useState(null)
  const [emailLoading, setEmailLoading] = useState(false)
  const [emailCopied,  setEmailCopied]  = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting,      setDeleting]      = useState(false)

  useEffect(() => {
    getMeeting(id)
      .then(m => {
        setMeeting(m)
        // Load extras in parallel — non-blocking
        // If any of these fail, the main content still shows
        Promise.allSettled([
          getMeetingHealth(id),
          getMeetingQuotes(id),
          getMeetingAITitle(id),
        ]).then(([h, q, t]) => {
          if (h.status === 'fulfilled') setHealth(h.value)
          if (q.status === 'fulfilled') setQuotes(q.value?.quotes || [])
          if (t.status === 'fulfilled') setAiTitle(t.value?.title)
        })
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  // FIX: deleting a meeting wasn't possible anywhere in the app — the only
  // way was editing the database directly, which is exactly what caused
  // deleted meetings' content to keep leaking into chat (see
  // DELETE /meetings/{id} in main.py for the full explanation). This now
  // goes through that endpoint, which cleans up Postgres AND ChromaDB.
  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteMeeting(id)
      toast.success('Meeting deleted', `"${meeting?.filename || 'Meeting'}" and all its data have been removed.`)
      navigate('/app/meetings', { replace: true })
    } catch (e) {
      toast.error('Delete failed', e.message)
      setDeleting(false)
    }
  }

  const handlePDFExport = async () => {
    setPdfLoading(true)
    try {
      const blob = await exportMeetingPDF(id)
      const url  = URL.createObjectURL(blob)
      const a    = Object.assign(document.createElement('a'), {
        href: url,
        download: `${meeting?.filename || 'meeting'}_report.pdf`,
      })
      a.click()
      URL.revokeObjectURL(url)
      toast.success('PDF exported', 'Your report is downloading.')
    } catch (e) {
      toast.error('Export failed', e.message)
    } finally {
      setPdfLoading(false)
    }
  }

  const handleFollowupEmail = async () => {
    setEmailLoading(true)
    setEmailModal(true)
    setEmailContent(null)
    try {
      const res = await getFollowupEmail(id)
      setEmailContent(res.email)
    } catch (e) {
      setEmailContent('Failed to generate email: ' + e.message)
    } finally {
      setEmailLoading(false)
    }
  }

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) return (
    <div>
      <Skeleton width="100px" height="28px" style={{ marginBottom: '24px' }} />
      <Skeleton width="50%"   height="36px" style={{ marginBottom: '12px' }} />
      <Skeleton width="30%"   height="16px" style={{ marginBottom: '32px' }} />
      <div style={{ display: 'flex', gap: '8px', marginBottom: '28px' }}>
        {[1,2,3,4,5].map(i => <Skeleton key={i} width="90px" height="36px" style={{ borderRadius: '10px' }} />)}
      </div>
      {[1,2,3].map(i => (
        <Card key={i} style={{ marginBottom: '18px' }}>
          <Skeleton width="35%"  height="16px" style={{ marginBottom: '14px' }} />
          <Skeleton width="100%" height="13px" style={{ marginBottom: '8px' }} />
          <Skeleton width="75%"  height="13px" />
        </Card>
      ))}
    </div>
  )

  if (error) return (
    <EmptyState
      icon="⚠️"
      title="Failed to load meeting"
      subtitle={error}
      action={<Button variant="secondary" onClick={() => navigate('/app/meetings')}>Back to Meetings</Button>}
    />
  )

  const intel = meeting?.intelligence

  // Tab definitions — count badges show live data
  const tabs = [
    { id: 'summary',    label: 'Summary',    icon: '📝' },
    { id: 'health',     label: 'Health',     icon: '❤️' },
    { id: 'transcript', label: 'Transcript', icon: '📄' },
    { id: 'speakers',   label: 'Speakers',   icon: '🎤' },   // NEW
    { id: 'tasks',      label: 'Tasks',      icon: '✅', count: intel?.action_items?.length || 0 },
  ]

  const stats = [
    { label: 'Topics',    value: intel?.topics?.length       ?? 0, color: T.cyanText,   bg: T.cyanBg,   icon: '🏷️' },
    { label: 'Decisions', value: intel?.decisions?.length    ?? 0, color: T.purpleText, bg: T.purpleBg, icon: '⚡' },
    { label: 'Actions',   value: intel?.action_items?.length ?? 0, color: T.orangeText, bg: T.orangeBg, icon: '✅' },
    { label: 'Words',     value: meeting?.transcript
        ? meeting.transcript.split(' ').length.toLocaleString()
        : 0,
      color: T.blueText, bg: T.blueBg, icon: '📝' },
  ]

  return (
    <div className="page-enter">

      {/* Back */}
      <button
        onClick={() => navigate('/app/meetings')}
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
        <ArrowLeft size={14} /> Back to Meetings
      </button>

      {/* Header */}
      <div className="anim-fade-up" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{
              fontSize: 'clamp(20px, 3vw, 28px)', fontWeight: 800,
              letterSpacing: '-0.04em', color: T.text,
              margin: '0 0 10px', lineHeight: 1.2,
            }}>
              {meeting.filename || 'Untitled Meeting'}
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: T.text3 }}>
                <Clock size={13} color={T.text4} />
                {fmt(meeting.created_at)}
              </span>
              <Badge color={T.emeraldText || T.emerald} bg={T.emeraldBg} dot>Processed</Badge>
              {health && (
                <Badge
                  color={health.overall_score >= 75 ? T.emerald : health.overall_score >= 50 ? (T.warning || '#f59e0b') : (T.danger || '#ef4444')}
                  bg={health.overall_score >= 75 ? T.emeraldBg : health.overall_score >= 50 ? (T.warningBg || '#fef3c7') : (T.dangerBg || '#fee2e2')}
                >
                  Health: {health.overall_score}/100
                </Badge>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <Button variant="ghost" size="sm"
              icon={linkCopied ? <Check size={13}/> : <Link size={13}/>}
              onClick={() => {
                navigator.clipboard.writeText(window.location.href)
                setLinkCopied(true)
                setTimeout(() => setLinkCopied(false), 2000)
              }}
            >
              {linkCopied ? 'Copied!' : 'Share'}
            </Button>
            <Button variant="ghost" size="sm" icon={<Download size={13}/>} onClick={handlePDFExport} loading={pdfLoading}>PDF</Button>
            <Button variant="ghost" size="sm" icon={<Download size={13}/>} onClick={() => downloadTXT(meeting, intel)}>TXT</Button>
            <Button variant="ghost" size="sm" icon={<Mail size={13}/>} onClick={handleFollowupEmail} loading={emailLoading}>Follow-up</Button>
            <WorkspaceAssign meetingId={id} T={T} />
            <Button size="sm" icon={<MessageSquare size={13}/>} onClick={() => navigate(`/app/chat?meeting=${id}`)}>Chat</Button>
            <Button
              variant="ghost" size="sm"
              icon={<Trash2 size={13} />}
              onClick={() => setDeleteConfirm(true)}
              style={{ color: T.danger, borderColor: `${T.danger}33` }}
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="anim-fade-up" style={{
        display: 'grid',
        gridTemplateColumns: grid?.cols4 || 'repeat(4, 1fr)',
        gap: '12px', marginBottom: '28px',
      }}>
        {stats.map(s => (
          <div key={s.label} style={{
            padding: '15px 18px', background: T.surface,
            border: `1px solid ${T.border}`, borderRadius: '14px',
            boxShadow: T.cardShadow || 'none',
            display: 'flex', alignItems: 'center', gap: '12px',
          }}>
            <div style={{
              width: 34, height: 34, borderRadius: '9px',
              background: s.bg, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '15px', flexShrink: 0,
            }}>
              {s.icon}
            </div>
            <div>
              <div style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.04em', color: T.text, lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: '11px', fontWeight: 600, color: T.text3, marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="anim-fade-up">
        <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />
      </div>

      {/* Tab content — key={activeTab} remounts on tab change → triggers page-enter animation */}
      <div key={activeTab}>
        {activeTab === 'summary'    && <SummaryTab    intel={intel} quotes={quotes} aiTitle={aiTitle} T={T} grid={grid} />}
        {activeTab === 'health'     && <HealthTab     health={health} T={T} />}
        {activeTab === 'transcript' && <TranscriptTab transcript={meeting?.transcript} T={T} />}
        {activeTab === 'speakers'   && <SpeakersTab   meetingId={id} T={T} />}
        {activeTab === 'tasks'      && <TasksTab      intel={intel} T={T} />}
      </div>

      {/* Follow-up Email Modal */}
      {emailModal && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.72)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 999, padding: '24px',
        }}>
          <div className="anim-scale-spring" style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: '20px', width: '100%', maxWidth: '640px',
            maxHeight: '80vh', display: 'flex', flexDirection: 'column',
            boxShadow: '0 32px 80px rgba(0,0,0,0.45)',
          }}>
            <div style={{ padding: '20px 24px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
                <div style={{ width: 34, height: 34, borderRadius: '9px', background: T.accentBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Mail size={17} color={T.accentLight} />
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Follow-up Email</div>
                  <div style={{ fontSize: '12px', color: T.text3 }}>AI generated · ready to send</div>
                </div>
              </div>
              <button
                onClick={() => { setEmailModal(false); setEmailContent(null); setEmailCopied(false) }}
                style={{ background: T.surface2, border: `1px solid ${T.border}`, borderRadius: '8px', width: 30, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: T.text3, fontSize: '16px', fontFamily: 'inherit' }}
              >×</button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
              {emailLoading ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '48px', gap: '16px' }}>
                  <div className="spinner" style={{ width: 24, height: 24 }} />
                  <div style={{ fontSize: '14px', color: T.text3 }}>Generating follow-up email...</div>
                </div>
              ) : (
                <pre style={{ fontSize: '13.5px', color: T.text2, lineHeight: 1.75, whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>
                  {emailContent}
                </pre>
              )}
            </div>
            {emailContent && !emailLoading && (
              <div style={{ padding: '16px 24px', borderTop: `1px solid ${T.border}`, display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <Button variant="ghost" size="sm" onClick={handleFollowupEmail}>Regenerate</Button>
                <Button size="sm"
                  icon={emailCopied ? <Check size={13}/> : <Copy size={13}/>}
                  onClick={() => { navigator.clipboard.writeText(emailContent); setEmailCopied(true); setTimeout(() => setEmailCopied(false), 2000) }}
                >
                  {emailCopied ? 'Copied!' : 'Copy Email'}
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* FIX: confirmation modal for the new delete action — deleting is
          irreversible (Postgres row + all intelligence + ChromaDB vectors),
          so this requires an explicit confirm click rather than deleting
          on the first click. */}
      {deleteConfirm && (
        <div style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.72)',
          backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 999, padding: '24px',
        }}>
          <div className="anim-scale-spring" style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: '20px', width: '100%', maxWidth: '420px',
            boxShadow: '0 32px 80px rgba(0,0,0,0.45)',
            padding: '24px',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px', marginBottom: '18px' }}>
              <div style={{
                width: 40, height: 40, borderRadius: '11px', flexShrink: 0,
                background: T.dangerBg, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
              }}>
                <AlertTriangle size={19} color={T.danger} />
              </div>
              <div>
                <div style={{ fontSize: '16px', fontWeight: 750, color: T.text, marginBottom: '4px' }}>
                  Delete this meeting?
                </div>
                <div style={{ fontSize: '13px', color: T.text3, lineHeight: 1.55 }}>
                  This permanently removes <strong>{meeting?.filename || 'this meeting'}</strong> —
                  its transcript, summary, action items, decisions, and chat
                  history. This can't be undone.
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <Button variant="ghost" size="sm" onClick={() => setDeleteConfirm(false)} disabled={deleting}>
                Cancel
              </Button>
              <Button
                size="sm"
                icon={<Trash2 size={13} />}
                onClick={handleDelete}
                loading={deleting}
                style={{ background: T.danger, boxShadow: 'none' }}
              >
                Delete Meeting
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}