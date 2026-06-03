// client/src/pages/MeetingDetail.jsx

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileText, Zap, CheckSquare,
  MessageSquare, Tag, Clock, Copy, Check,
  Download, Share2, BarChart2, Link
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeeting } from '../api/client'
import {
  Card, Button, Badge,
  EmptyState, Skeleton,
} from '../components/ui'

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric',
      year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso.slice(0, 16) }
}

function priorityColors(p, T) {
  if (p === 'high') return { color: T.danger,  bg: T.dangerBg  }
  if (p === 'low')  return { color: T.emerald, bg: T.emeraldBg }
  return                    { color: T.warning, bg: T.warningBg }
}

// ── Copy button ────────────────────────────────────────────────────────────────
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
        color: copied ? T.emerald : T.text3,
        background: copied ? T.emeraldBg : T.surface2,
        border: `1px solid ${copied ? T.emerald + '44' : T.border}`,
        cursor: 'pointer', transition: 'all 0.15s ease',
      }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

// ── Section header ─────────────────────────────────────────────────────────────
function SectionHead({ icon, title, count, color, bg }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '18px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
        <div style={{
          width: '34px', height: '34px', borderRadius: '9px',
          background: bg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {icon}
        </div>
        <span style={{
          fontSize: '16px', fontWeight: 700,
          letterSpacing: '-0.03em', color: T.text,
        }}>
          {title}
        </span>
      </div>
      {count !== undefined && (
        <span style={{
          padding: '2px 10px', borderRadius: '99px',
          fontSize: '12px', fontWeight: 700,
          color, background: bg,
        }}>
          {count}
        </span>
      )}
    </div>
  )
}

// ── Download helpers ───────────────────────────────────────────────────────────
function downloadJSON(meeting, intel) {
  const data = {
    id:         meeting.id,
    filename:   meeting.filename,
    created_at: meeting.created_at,
    transcript: meeting.transcript,
    intelligence: intel,
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `${meeting.filename || 'meeting'}_report.json`
  a.click()
  URL.revokeObjectURL(url)
}

function downloadTXT(meeting, intel) {
  const lines = [
    `MEETING REPORT`,
    `═══════════════════════════════════════`,
    `File:       ${meeting.filename || 'Untitled'}`,
    `Date:       ${fmt(meeting.created_at)}`,
    ``,
    `SUMMARY`,
    `───────────────────────────────────────`,
    intel?.summary || 'No summary.',
    ``,
  ]

  if (intel?.topics?.length) {
    lines.push(`TOPICS`, `───────────────────────────────────────`)
    intel.topics.forEach(t => lines.push(`• ${t.title}${t.description ? ` — ${t.description}` : ''}`))
    lines.push(``)
  }

  if (intel?.decisions?.length) {
    lines.push(`DECISIONS`, `───────────────────────────────────────`)
    intel.decisions.forEach((d, i) => {
      lines.push(`${i + 1}. ${d.decision}`)
      if (d.rationale) lines.push(`   ↳ ${d.rationale}`)
    })
    lines.push(``)
  }

  if (intel?.action_items?.length) {
    lines.push(`ACTION ITEMS`, `───────────────────────────────────────`)
    intel.action_items.forEach((item, i) => {
      lines.push(`${i + 1}. ${item.task}`)
      if (item.owner)    lines.push(`   Owner:    ${item.owner}`)
      if (item.deadline) lines.push(`   Deadline: ${item.deadline}`)
      if (item.priority) lines.push(`   Priority: ${item.priority}`)
    })
    lines.push(``)
  }

  lines.push(`TRANSCRIPT`, `───────────────────────────────────────`)
  lines.push(meeting.transcript || 'No transcript.')

  const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `${meeting.filename || 'meeting'}_report.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function MeetingDetail() {
  const { T }    = useTheme()
  const { id }   = useParams()
  const navigate = useNavigate()

  const [meeting,  setMeeting]  = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [linkCopied, setLinkCopied] = useState(false)

  useEffect(() => {
    getMeeting(id)
      .then(setMeeting)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) return (
    <div>
      <Skeleton width="100px" height="28px" style={{ borderRadius: '8px', marginBottom: '24px' }} />
      <Skeleton width="50%" height="36px" style={{ marginBottom: '12px' }} />
      <Skeleton width="30%" height="16px" style={{ marginBottom: '32px' }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '14px', marginBottom: '28px' }}>
        {[1,2,3,4].map(i => (
          <Card key={i} style={{ padding: '20px' }}>
            <Skeleton width="60%" height="11px" style={{ marginBottom: '12px' }} />
            <Skeleton width="35%" height="32px" />
          </Card>
        ))}
      </div>
      {[1,2,3].map(i => (
        <Card key={i} style={{ marginBottom: '18px' }}>
          <Skeleton width="35%" height="16px" style={{ marginBottom: '14px' }} />
          <Skeleton width="100%" height="13px" style={{ marginBottom: '8px' }} />
          <Skeleton width="75%" height="13px" />
        </Card>
      ))}
    </div>
  )

  // ── Error ──────────────────────────────────────────────────────────────────
  if (error) return (
    <EmptyState
      icon="⚠️"
      title="Failed to load meeting"
      subtitle={error}
      action={
        <Button variant="secondary" onClick={() => navigate('/meetings')}>
          Back to Meetings
        </Button>
      }
    />
  )

  const intel = meeting?.intelligence

  // ── Quick stats ────────────────────────────────────────────────────────────
  const quickStats = [
    {
      label: 'Topics',
      value: intel?.topics?.length       ?? 0,
      color: T.cyanText,   bg: T.cyanBg,   icon: '🏷️',
    },
    {
      label: 'Decisions',
      value: intel?.decisions?.length    ?? 0,
      color: T.purpleText, bg: T.purpleBg, icon: '⚡',
    },
    {
      label: 'Action Items',
      value: intel?.action_items?.length ?? 0,
      color: T.orangeText, bg: T.orangeBg, icon: '✅',
    },
    {
      label: 'Words',
      value: meeting?.transcript
        ? meeting.transcript.split(' ').length.toLocaleString()
        : 0,
      color: T.blueText,   bg: T.blueBg,   icon: '📝',
    },
  ]

  return (
    <div>

      {/* ── Back button ── */}
      <button
        onClick={() => navigate('/meetings')}
        className="anim-fade-in"
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          fontSize: '13px', fontWeight: 600, color: T.text3,
          background: 'none', border: 'none', cursor: 'pointer',
          marginBottom: '20px', padding: 0,
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={e => e.currentTarget.style.color = T.text}
        onMouseLeave={e => e.currentTarget.style.color = T.text3}
      >
        <ArrowLeft size={14} /> Back to Meetings
      </button>

      {/* ── Header ── */}
      <div className="anim-fade-up" style={{ marginBottom: '28px' }}>
        <div style={{
          display: 'flex', alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap', gap: '16px',
        }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <h1 style={{
              fontSize: '28px', fontWeight: 800,
              letterSpacing: '-0.04em', color: T.text,
              margin: '0 0 10px', lineHeight: 1.2,
            }}>
              {meeting.filename || 'Untitled Meeting'}
            </h1>
            <div style={{
              display: 'flex', alignItems: 'center',
              gap: '14px', flexWrap: 'wrap',
            }}>
              <span style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                fontSize: '13px', color: T.text3,
              }}>
                <Clock size={13} color={T.text4} />
                {fmt(meeting.created_at)}
              </span>
              <Badge color={T.emeraldText} bg={T.emeraldBg}>
                Processed
              </Badge>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <Button
              variant="ghost" size="sm"
              icon={linkCopied ? <Check size={13} /> : <Link size={13} />}
              onClick={() => {
                navigator.clipboard.writeText(window.location.href)
                setLinkCopied(true)
                setTimeout(() => setLinkCopied(false), 2000)
              }}
            >
              {linkCopied ? 'Copied!' : 'Share Link'}
            </Button>
            <Button
              variant="ghost" size="sm"
              icon={<Download size={13} />}
              onClick={() => downloadTXT(meeting, intel)}
            >
              Download TXT
            </Button>
            <Button
              variant="ghost" size="sm"
              icon={<Download size={13} />}
              onClick={() => downloadJSON(meeting, intel)}
            >
              Download JSON
            </Button>
            <Button
              size="sm"
              icon={<MessageSquare size={13} />}
              onClick={() => navigate(`/chat?meeting=${id}`)}
            >
              Chat
            </Button>
          </div>
        </div>
      </div>

      {/* ── Quick stats bar ── */}
      <div
        className="anim-fade-up anim-fade-up-1"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px', marginBottom: '28px',
        }}
      >
        {quickStats.map((s, i) => (
          <div key={s.label} style={{
            padding: '16px 18px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: '14px',
            boxShadow: T.cardShadow,
            display: 'flex', alignItems: 'center', gap: '12px',
          }}>
            <div style={{
              width: '36px', height: '36px',
              borderRadius: '9px', background: s.bg,
              display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '16px',
              flexShrink: 0,
            }}>
              {s.icon}
            </div>
            <div>
              <div style={{
                fontSize: '22px', fontWeight: 800,
                letterSpacing: '-0.04em', color: T.text,
                lineHeight: 1,
              }}>
                {s.value}
              </div>
              <div style={{
                fontSize: '11px', fontWeight: 600,
                color: T.text3, marginTop: '3px',
                letterSpacing: '0.04em', textTransform: 'uppercase',
              }}>
                {s.label}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── No intelligence fallback ── */}
      {!intel ? (
        <Card>
          <EmptyState
            icon="🤖"
            title="No intelligence data"
            subtitle="This meeting has not been analyzed yet."
          />
        </Card>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 380px',
          gap: '20px',
          alignItems: 'start',
        }}>

          {/* ── LEFT column ── */}
          <div>

            {/* Summary */}
            <div className="anim-fade-up anim-fade-up-2">
              <Card style={{ marginBottom: '18px' }}>
                <SectionHead
                  icon={<FileText size={16} color={T.blueText} />}
                  title="Summary"
                  color={T.blueText}
                  bg={T.blueBg}
                />
                <p style={{
                  fontSize: '16px', fontWeight: 400,
                  color: T.text2, lineHeight: 1.8,
                  margin: 0,
                }}>
                  {intel.summary || 'No summary available.'}
                </p>
              </Card>
            </div>

            {/* Decisions */}
            <div className="anim-fade-up anim-fade-up-3">
              <Card style={{ marginBottom: '18px' }}>
                <SectionHead
                  icon={<Zap size={16} color={T.purpleText} />}
                  title="Decisions"
                  count={intel.decisions?.length}
                  color={T.purpleText}
                  bg={T.purpleBg}
                />
                {intel.decisions?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {intel.decisions.map((d, i) => (
                      <div key={i} style={{
                        padding: '14px 16px',
                        borderRadius: '10px',
                        background: T.purpleBg,
                        border: `1px solid ${T.purple}22`,
                      }}>
                        <div style={{
                          fontSize: '14px', fontWeight: 600,
                          color: T.text, lineHeight: 1.55,
                          marginBottom: d.rationale ? '6px' : 0,
                        }}>
                          {d.decision}
                        </div>
                        {d.rationale && (
                          <div style={{
                            fontSize: '13px', color: T.text3,
                            fontStyle: 'italic', lineHeight: 1.5,
                          }}>
                            ↳ {d.rationale}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '14px', color: T.text3 }}>
                    No decisions recorded.
                  </div>
                )}
              </Card>
            </div>

            {/* Action Items */}
            <div className="anim-fade-up anim-fade-up-4">
              <Card style={{ marginBottom: '18px' }}>
                <SectionHead
                  icon={<CheckSquare size={16} color={T.orangeText} />}
                  title="Action Items"
                  count={intel.action_items?.length}
                  color={T.orangeText}
                  bg={T.orangeBg}
                />
                {intel.action_items?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
                    {intel.action_items.map((item, i) => {
                      const pc = priorityColors(item.priority, T)
                      return (
                        <div key={i} style={{
                          display: 'flex', alignItems: 'flex-start',
                          justifyContent: 'space-between', gap: '14px',
                          padding: '13px 16px',
                          borderRadius: '10px',
                          background: T.surface2,
                          border: `1px solid ${T.border}`,
                        }}>
                          <div style={{ flex: 1 }}>
                            <div style={{
                              fontSize: '14px', fontWeight: 600,
                              color: T.text, lineHeight: 1.5, marginBottom: '6px',
                            }}>
                              {item.task}
                            </div>
                            <div style={{
                              display: 'flex', flexWrap: 'wrap',
                              gap: '10px', fontSize: '12px', color: T.text3,
                            }}>
                              {item.owner    && <span>👤 {item.owner}</span>}
                              {item.deadline && <span>📅 {item.deadline}</span>}
                            </div>
                          </div>
                          <div style={{
                            display: 'flex', flexDirection: 'column',
                            gap: '5px', alignItems: 'flex-end', flexShrink: 0,
                          }}>
                            <Badge color={pc.color} bg={pc.bg}>
                              {item.priority || 'medium'}
                            </Badge>
                            <Badge
                              color={item.status === 'open' ? T.warning : T.emerald}
                              bg={item.status === 'open' ? T.warningBg : T.emeraldBg}
                            >
                              {item.status || 'open'}
                            </Badge>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div style={{ fontSize: '14px', color: T.text3 }}>
                    No action items found.
                  </div>
                )}
              </Card>
            </div>

          </div>

          {/* ── RIGHT column ── */}
          <div style={{ position: 'sticky', top: '24px' }}>

            {/* Topics */}
            <div className="anim-fade-up anim-fade-up-2">
              <Card style={{ marginBottom: '18px' }}>
                <SectionHead
                  icon={<Tag size={16} color={T.cyanText} />}
                  title="Topics"
                  count={intel.topics?.length}
                  color={T.cyanText}
                  bg={T.cyanBg}
                />
                {intel.topics?.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {intel.topics.map((t, i) => (
                      <div key={i} style={{
                        padding: '10px 14px',
                        borderRadius: '9px',
                        background: T.cyanBg,
                        border: `1px solid ${T.cyan}22`,
                      }}>
                        <div style={{
                          fontSize: '13px', fontWeight: 650,
                          color: T.cyanText, marginBottom: t.description ? '3px' : 0,
                        }}>
                          {t.title}
                        </div>
                        {t.description && (
                          <div style={{ fontSize: '12px', color: T.text3, lineHeight: 1.5 }}>
                            {t.description}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '14px', color: T.text3 }}>
                    No topics identified.
                  </div>
                )}
              </Card>
            </div>

            {/* Transcript */}
            <div className="anim-fade-up anim-fade-up-3">
              <Card style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '18px 20px',
                  borderBottom: `1px solid ${T.border}`,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                      width: '30px', height: '30px', borderRadius: '8px',
                      background: T.surface2,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <FileText size={15} color={T.text3} />
                    </div>
                    <span style={{
                      fontSize: '15px', fontWeight: 700,
                      color: T.text, letterSpacing: '-0.02em',
                    }}>
                      Transcript
                    </span>
                  </div>
                  <CopyBtn text={meeting.transcript || ''} />
                </div>
                <div style={{
                  maxHeight: '420px', overflowY: 'auto',
                  padding: '18px 20px',
                  fontSize: '13.5px', fontWeight: 400,
                  color: T.text2, lineHeight: 1.85,
                  letterSpacing: '-0.005em',
                }}>
                  {meeting.transcript || 'No transcript available.'}
                </div>
              </Card>
            </div>

          </div>
        </div>
      )}
    </div>
  )
}