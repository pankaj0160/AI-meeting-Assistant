// client/src/pages/Dashboard.jsx

import { getMeetings, getStats, reindexAll } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Upload, Mic, Zap,
  CheckSquare, FileText, BarChart2,
  Search, RefreshCw, TrendingUp, Clock,
  Sparkles, Activity,
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import {
  PageHeader, Card, StatCard,
  Badge, Button, EmptyState, Skeleton
} from '../components/ui'

/* ── Greeting ── */
function getGreeting(userName = 'there') {
  const hour = new Date().getHours()
  if (hour < 12) return {
    eyebrow: 'Good Morning',
    emoji: '☀️',
    title: `Welcome back, ${userName}`,
    subtitle: 'Turn today\'s conversations into decisions, actions, and outcomes.',
  }
  if (hour < 17) return {
    eyebrow: 'Good Afternoon',
    emoji: '🚀',
    title: `Ready to stay aligned, ${userName}?`,
    subtitle: 'Your AI meeting assistant is standing by to surface insights instantly.',
  }
  return {
    eyebrow: 'Good Evening',
    emoji: '🌙',
    title: `Let's wrap up well, ${userName}`,
    subtitle: 'Review summaries, confirm action items, and close the loop before tomorrow.',
  }
}

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch { return iso.slice(0, 10) }
}

function timeAgo(iso) {
  if (!iso) return ''
  try {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return fmt(iso)
  } catch { return '' }
}

/* ── Meeting Row ── */
function MeetingRow({ meeting, onClick, index }) {
  const { T, isDark } = useTheme()
  const [hovered, setHovered] = useState(false)

  const HUES = ['#6366f1', '#a855f7', '#06b6d4', '#10b981', '#f97316', '#3b82f6', '#f59e0b']
  const hue = HUES[index % HUES.length]

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '13px 16px',
        borderRadius: '12px',
        background: hovered
          ? isDark ? `${hue}0a` : `${hue}07`
          : 'transparent',
        border: `1px solid ${hovered ? `${hue}25` : 'transparent'}`,
        cursor: 'pointer',
        transition: 'all 0.15s var(--ease-smooth)',
        gap: '16px',
      }}
    >
      {/* Left: icon + title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '13px', minWidth: 0 }}>
        <div style={{
          width: '40px', height: '40px',
          borderRadius: '11px',
          background: `${hue}18`,
          border: `1px solid ${hue}25`,
          flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'transform 0.2s var(--ease-spring)',
          transform: hovered ? 'scale(1.06)' : 'scale(1)',
        }}>
          <Mic size={16} color={hue} strokeWidth={2.1} />
        </div>

        <div style={{ minWidth: 0 }}>
          <div style={{
            fontSize: '14px',
            fontWeight: 600,
            color: T.text,
            fontFamily: 'var(--font-body)',
            letterSpacing: '-0.02em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '360px',
          }}>
            {meeting.filename || 'Untitled Meeting'}
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginTop: '3px',
          }}>
            <Clock size={10} color={T.text3} />
            <span style={{
              fontSize: '11.5px',
              color: T.text3,
              fontFamily: 'var(--font-body)',
            }}>
              {timeAgo(meeting.created_at)}
            </span>
            <span style={{ color: T.text4, fontSize: '10px' }}>·</span>
            <span style={{
              fontSize: '11.5px',
              color: T.text4,
              fontFamily: 'var(--font-mono)',
            }}>
              {fmt(meeting.created_at)}
            </span>
          </div>
        </div>
      </div>

      {/* Right: badge + arrow */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <span style={{
          padding: '3px 10px',
          borderRadius: '99px',
          fontSize: '10.5px',
          fontWeight: 700,
          fontFamily: 'var(--font-body)',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
          background: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(5,150,105,0.09)',
          color: T.emeraldText,
          border: `1px solid ${T.emerald}28`,
        }}>
          Processed
        </span>
        <ArrowRight
          size={14}
          color={hue}
          style={{
            opacity: hovered ? 1 : 0,
            transform: hovered ? 'translateX(0)' : 'translateX(-6px)',
            transition: 'all 0.18s ease',
          }}
        />
      </div>
    </div>
  )
}

/* ── Stat Card ── */
function PremiumStatCard({ label, value, icon, color, bg, trend, delay = 0 }) {
  const { T, isDark } = useTheme()
  const [hovered, setHovered] = useState(false)

  return (
    <div
      className={`anim-fade-up`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '22px',
        borderRadius: '18px',
        background: T.surface,
        border: `1px solid ${hovered ? color + '30' : T.border}`,
        boxShadow: hovered
          ? `${T.cardShadowHover}, 0 0 0 1px ${color}15`
          : T.cardShadow,
        cursor: 'default',
        transition: 'all 0.2s var(--ease-smooth)',
        animationDelay: `${delay}s`,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        bottom: '-20px', right: '-20px',
        width: '100px', height: '100px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}18, transparent 70%)`,
        transition: 'opacity 0.2s ease',
        opacity: hovered ? 1 : 0.5,
        pointerEvents: 'none',
      }} />

      {/* Icon */}
      <div style={{
        width: '42px', height: '42px',
        borderRadius: '12px',
        background: bg,
        border: `1px solid ${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '20px',
        marginBottom: '16px',
        transition: 'transform 0.2s var(--ease-spring)',
        transform: hovered ? 'scale(1.08)' : 'scale(1)',
      }}>
        {icon}
      </div>

      {/* Value */}
      <div style={{
        fontSize: '32px',
        fontWeight: 800,
        fontFamily: 'var(--font-display)',
        letterSpacing: '-0.04em',
        color: color,
        lineHeight: 1,
        marginBottom: '6px',
      }}>
        {value}
      </div>

      {/* Label */}
      <div style={{
        fontSize: '12.5px',
        fontWeight: 500,
        color: T.text3,
        fontFamily: 'var(--font-body)',
        letterSpacing: '0.01em',
      }}>
        {label}
      </div>

      {/* Trend */}
      {trend && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          marginTop: '10px',
        }}>
          <TrendingUp size={10} color={T.emeraldText} />
          <span style={{
            fontSize: '11px',
            color: T.emeraldText,
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
          }}>
            {trend}
          </span>
        </div>
      )}
    </div>
  )
}

/* ── Quick Action Card ── */
function QuickAction({ icon, label, sub, onClick, color, bg }) {
  const { T } = useTheme()
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '20px',
        borderRadius: '16px',
        background: T.surface,
        border: `1px solid ${hovered ? color + '30' : T.border}`,
        boxShadow: hovered ? T.cardShadowHover : T.cardShadow,
        cursor: 'pointer',
        transition: 'all 0.18s var(--ease-smooth)',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
      }}
    >
      <div style={{
        width: '40px', height: '40px',
        borderRadius: '11px',
        background: bg,
        border: `1px solid ${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '14px',
        transition: 'transform 0.2s var(--ease-spring)',
        transform: hovered ? 'scale(1.10) rotate(-3deg)' : 'scale(1)',
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: '14.5px',
        fontWeight: 700,
        color: hovered ? color : T.text,
        fontFamily: 'var(--font-display)',
        letterSpacing: '-0.02em',
        marginBottom: '4px',
        transition: 'color 0.15s ease',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '12px',
        color: T.text3,
        fontFamily: 'var(--font-body)',
      }}>
        {sub}
      </div>
    </div>
  )
}

/* ══ DASHBOARD ══ */
export default function Dashboard() {
  const { T, isDark } = useTheme()
  const { user }      = useAuth()
  const navigate      = useNavigate()
  const greeting      = getGreeting(user?.full_name?.split(' ')[0] || 'there')

  const [meetings,   setMeetings]   = useState([])
  const [stats,      setStats]      = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [query,      setQuery]      = useState('')
  const [reindexing, setReindexing] = useState(false)
  const [reindexMsg, setReindexMsg] = useState(null)
  const [searchFocus, setSearchFocus] = useState(false)

  useEffect(() => {
    Promise.all([
      getMeetings().catch(() => []),
      getStats().catch(() => null),
    ]).then(([m, s]) => {
      setMeetings(m)
      setStats(s)
    }).finally(() => setLoading(false))
  }, [])

  const filtered = meetings.filter(m =>
    (m.filename || '').toLowerCase().includes(query.toLowerCase())
  )

  const handleReindex = async () => {
    setReindexing(true)
    setReindexMsg(null)
    try {
      const res = await reindexAll()
      setReindexMsg(`✓ Reindexed ${res.indexed} of ${res.total} meetings`)
    } catch {
      setReindexMsg('Reindex failed — is the backend running?')
    } finally {
      setReindexing(false)
      setTimeout(() => setReindexMsg(null), 4000)
    }
  }

  const statCards = [
    {
      label: 'Meetings Processed',
      value: loading ? '—' : (stats?.total_meetings ?? meetings.length),
      icon: '🎙️',
      color: '#818cf8',
      bg: isDark ? 'rgba(99,102,241,0.14)' : 'rgba(99,102,241,0.09)',
    },
    {
      label: 'Decisions Found',
      value: loading ? '—' : (stats?.total_decisions ?? '—'),
      icon: '⚡',
      color: '#c084fc',
      bg: isDark ? 'rgba(168,85,247,0.14)' : 'rgba(168,85,247,0.09)',
    },
    {
      label: 'Action Items',
      value: loading ? '—' : (stats?.total_actions ?? '—'),
      icon: '✅',
      color: '#fb923c',
      bg: isDark ? 'rgba(249,115,22,0.14)' : 'rgba(249,115,22,0.09)',
    },
    {
      label: 'Topics Detected',
      value: loading ? '—' : (stats?.total_topics ?? '—'),
      icon: '🏷️',
      color: '#22d3ee',
      bg: isDark ? 'rgba(6,182,212,0.14)' : 'rgba(6,182,212,0.09)',
    },
  ]

  return (
    <div>

      {/* ══ HERO GREETING ══ */}
      <div className="anim-fade-up" style={{ marginBottom: '36px' }}>
        {/* Eyebrow */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '10px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 12px',
            borderRadius: '99px',
            background: isDark ? 'rgba(99,102,241,0.12)' : 'rgba(80,70,228,0.08)',
            border: `1px solid ${isDark ? 'rgba(99,102,241,0.25)' : 'rgba(80,70,228,0.18)'}`,
          }}>
            <Activity size={10} color="#818cf8" />
            <span style={{
              fontSize: '11px',
              fontWeight: 700,
              color: '#818cf8',
              textTransform: 'uppercase',
              letterSpacing: '0.10em',
              fontFamily: 'var(--font-body)',
            }}>
              {greeting.eyebrow}
            </span>
            <span style={{ fontSize: '12px' }}>{greeting.emoji}</span>
          </div>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '24px',
          flexWrap: 'wrap',
        }}>
          <div>
            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: '36px',
              fontWeight: 800,
              letterSpacing: '-0.04em',
              color: T.text,
              lineHeight: 1.1,
              marginBottom: '8px',
            }}>
              {greeting.title}
            </h1>
            <p style={{
              fontSize: '15px',
              color: T.text3,
              fontFamily: 'var(--font-body)',
              fontWeight: 400,
              lineHeight: 1.6,
              maxWidth: '520px',
            }}>
              {greeting.subtitle}
            </p>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexShrink: 0 }}>
            <button
              onClick={handleReindex}
              disabled={reindexing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '7px',
                padding: '9px 16px',
                borderRadius: '10px',
                border: `1px solid ${T.border}`,
                background: T.surface,
                color: T.text2,
                fontSize: '13px',
                fontWeight: 600,
                fontFamily: 'var(--font-body)',
                cursor: reindexing ? 'not-allowed' : 'pointer',
                opacity: reindexing ? 0.65 : 1,
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => {
                if (!reindexing) {
                  e.currentTarget.style.borderColor = T.border2
                  e.currentTarget.style.color = T.text
                }
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = T.border
                e.currentTarget.style.color = T.text2
              }}
            >
              <RefreshCw
                size={13}
                style={{ animation: reindexing ? 'spinSlow 0.7s linear infinite' : 'none' }}
              />
              {reindexing ? 'Reindexing…' : 'Reindex'}
            </button>

            <button
              onClick={() => navigate('/app/upload')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 20px',
                borderRadius: '10px',
                border: 'none',
                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                color: '#fff',
                fontSize: '13.5px',
                fontWeight: 700,
                fontFamily: 'var(--font-body)',
                cursor: 'pointer',
                letterSpacing: '-0.01em',
                boxShadow: '0 4px 18px rgba(99,102,241,0.40)',
                transition: 'all 0.18s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-1px)'
                e.currentTarget.style.boxShadow = '0 8px 28px rgba(99,102,241,0.55)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 18px rgba(99,102,241,0.40)'
              }}
            >
              <Upload size={14} />
              Upload Meeting
            </button>
          </div>
        </div>
      </div>

      {/* Reindex toast */}
      {reindexMsg && (
        <div className="anim-fade-in" style={{
          padding: '12px 18px',
          borderRadius: '12px',
          background: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(5,150,105,0.09)',
          border: `1px solid ${T.emerald}30`,
          fontSize: '13px',
          fontWeight: 600,
          fontFamily: 'var(--font-body)',
          color: T.emeraldText,
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Sparkles size={14} color={T.emeraldText} />
          {reindexMsg}
        </div>
      )}

      {/* ══ STAT CARDS ══ */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px',
        marginBottom: '32px',
      }}>
        {statCards.map((s, i) => (
          loading ? (
            <div key={s.label} style={{
              height: '148px',
              borderRadius: '18px',
              overflow: 'hidden',
            }}>
              <div className="skeleton" style={{ width: '100%', height: '100%' }} />
            </div>
          ) : (
            <PremiumStatCard key={s.label} delay={i * 0.07} {...s} />
          )
        ))}
      </div>

      {/* ══ RECENT MEETINGS ══ */}
      <div className="anim-fade-up anim-fade-up-3" style={{ marginBottom: '28px' }}>
        <div style={{
          padding: '0',
          borderRadius: '20px',
          background: T.surface,
          border: `1px solid ${T.border}`,
          boxShadow: T.cardShadow,
          overflow: 'hidden',
        }}>

          {/* Card header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 24px',
            borderBottom: `1px solid ${T.border}`,
            flexWrap: 'wrap',
            gap: '14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '32px', height: '32px',
                borderRadius: '9px',
                background: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(80,70,228,0.09)',
                border: '1px solid rgba(99,102,241,0.25)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Mic size={14} color="#818cf8" strokeWidth={2.1} />
              </div>

              <span style={{
                fontSize: '16px',
                fontWeight: 750,
                color: T.text,
                fontFamily: 'var(--font-display)',
                letterSpacing: '-0.03em',
              }}>
                Recent Meetings
              </span>

              {meetings.length > 0 && (
                <span style={{
                  padding: '2px 9px',
                  borderRadius: '99px',
                  fontSize: '11px',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  background: isDark ? 'rgba(99,102,241,0.15)' : 'rgba(80,70,228,0.09)',
                  color: '#818cf8',
                  border: '1px solid rgba(99,102,241,0.22)',
                }}>
                  {meetings.length}
                </span>
              )}
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              {/* Search */}
              <div style={{ position: 'relative' }}>
                <Search size={12} color={searchFocus ? '#818cf8' : T.text3} style={{
                  position: 'absolute',
                  left: '11px', top: '50%',
                  transform: 'translateY(-50%)',
                  transition: 'color 0.15s ease',
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
                    width: '180px',
                    border: `1px solid ${searchFocus ? '#6366f1' : T.inputBorder}`,
                    background: T.inputBg,
                    color: T.text,
                    fontSize: '13px',
                    fontFamily: 'var(--font-body)',
                    outline: 'none',
                    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                    boxShadow: searchFocus ? `0 0 0 3px rgba(99,102,241,0.12)` : 'none',
                  }}
                />
              </div>

              <button
                onClick={() => navigate('/app/meetings')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  borderRadius: '10px',
                  border: `1px solid ${T.border}`,
                  background: 'transparent',
                  color: T.text3,
                  fontSize: '12.5px',
                  fontWeight: 600,
                  fontFamily: 'var(--font-body)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.color = T.text
                  e.currentTarget.style.borderColor = T.border2
                  e.currentTarget.style.background = T.surface2
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = T.text3
                  e.currentTarget.style.borderColor = T.border
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                View all
                <ArrowRight size={12} />
              </button>
            </div>
          </div>

          {/* Meeting list */}
          <div style={{ padding: '10px 8px' }}>
            {loading ? (
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[1, 2, 3].map(i => (
                  <div key={i} style={{
                    display: 'flex', gap: '13px',
                    alignItems: 'center',
                    padding: '4px 12px',
                  }}>
                    <div className="skeleton" style={{ width: '40px', height: '40px', borderRadius: '11px', flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <div className="skeleton" style={{ width: '52%', height: '14px', marginBottom: '8px', borderRadius: '6px' }} />
                      <div className="skeleton" style={{ width: '25%', height: '11px', borderRadius: '6px' }} />
                    </div>
                    <div className="skeleton" style={{ width: '80px', height: '22px', borderRadius: '99px' }} />
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '48px 24px', textAlign: 'center' }}>
                <div style={{ fontSize: '40px', marginBottom: '14px' }}>
                  {query ? '🔍' : '🎙️'}
                </div>
                <div style={{
                  fontSize: '16px',
                  fontWeight: 700,
                  color: T.text,
                  fontFamily: 'var(--font-display)',
                  letterSpacing: '-0.02em',
                  marginBottom: '8px',
                }}>
                  {query ? `No results for "${query}"` : 'No meetings yet'}
                </div>
                <div style={{
                  fontSize: '13.5px',
                  color: T.text3,
                  fontFamily: 'var(--font-body)',
                  marginBottom: '20px',
                }}>
                  {query
                    ? 'Try a different search term.'
                    : 'Upload your first meeting recording to get started.'
                  }
                </div>
                {!query && (
                  <button
                    onClick={() => navigate('/app/upload')}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 22px',
                      borderRadius: '10px',
                      border: 'none',
                      background: 'linear-gradient(135deg, #6366f1, #a855f7)',
                      color: '#fff',
                      fontSize: '13.5px',
                      fontWeight: 700,
                      fontFamily: 'var(--font-body)',
                      cursor: 'pointer',
                      boxShadow: '0 4px 16px rgba(99,102,241,0.38)',
                    }}
                  >
                    <Upload size={14} />
                    Upload Meeting
                  </button>
                )}
              </div>
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

      {/* ══ QUICK ACTIONS ══ */}
      {!loading && meetings.length > 0 && (
        <div className="anim-fade-up anim-fade-up-4">
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '14px',
          }}>
            <Zap size={13} color="#818cf8" fill="#818cf8" />
            <span style={{
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.10em',
              textTransform: 'uppercase',
              color: T.text3,
              fontFamily: 'var(--font-body)',
            }}>
              Quick Actions
            </span>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '14px',
          }}>
            {[
              {
                icon: <Upload size={17} color="#818cf8" />,
                label: 'Upload',
                sub: 'Add a new recording',
                to: '/app/upload',
                color: '#818cf8',
                bg: isDark ? 'rgba(99,102,241,0.14)' : 'rgba(80,70,228,0.09)',
              },
              {
                icon: <FileText size={17} color="#c084fc" />,
                label: 'Summaries',
                sub: 'AI-generated insights',
                to: '/app/summaries',
                color: '#c084fc',
                bg: isDark ? 'rgba(168,85,247,0.14)' : 'rgba(124,58,237,0.09)',
              },
              {
                icon: <CheckSquare size={17} color="#fb923c" />,
                label: 'Tasks',
                sub: 'Track action items',
                to: '/app/tasks',
                color: '#fb923c',
                bg: isDark ? 'rgba(249,115,22,0.14)' : 'rgba(234,88,12,0.09)',
              },
              {
                icon: <BarChart2 size={17} color="#22d3ee" />,
                label: 'Analytics',
                sub: 'Trends & patterns',
                to: '/app/analytics',
                color: '#22d3ee',
                bg: isDark ? 'rgba(6,182,212,0.14)' : 'rgba(8,145,178,0.09)',
              },
            ].map(item => (
              <QuickAction
                key={item.label}
                {...item}
                onClick={() => navigate(item.to)}
              />
            ))}
          </div>
        </div>
      )}

    </div>
  )
}