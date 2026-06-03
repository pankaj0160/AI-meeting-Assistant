// client/src/pages/Dashboard.jsx

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, Upload, Mic, Zap,
  CheckSquare, FileText, BarChart2,
  Search, RefreshCw
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeetings, getStats, reindexAll } from '../api/client'
import {
  PageHeader, Card, StatCard,
  Badge, Button, EmptyState, Skeleton
} from '../components/ui'

function greeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function fmt(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
    })
  } catch { return iso.slice(0, 10) }
}

function MeetingRow({ meeting, onClick }) {
  const { T } = useTheme()
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '13px 16px', borderRadius: '10px',
        background: hovered ? T.surfaceHover : 'transparent',
        border: `1px solid ${hovered ? T.border2 : 'transparent'}`,
        cursor: 'pointer', transition: 'all 0.15s ease', gap: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '13px', minWidth: 0 }}>
        <div style={{
          width: '38px', height: '38px', borderRadius: '9px',
          background: T.accentBg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Mic size={16} color={T.accentLight} strokeWidth={2} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontSize: '14px', fontWeight: 600, color: T.text,
            letterSpacing: '-0.02em', whiteSpace: 'nowrap',
            overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '380px',
          }}>
            {meeting.filename || 'Untitled Meeting'}
          </div>
          <div style={{ fontSize: '12px', color: T.text3, marginTop: '2px' }}>
            {fmt(meeting.created_at)}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <Badge color={T.emeraldText} bg={T.emeraldBg}>Processed</Badge>
        <ArrowRight size={15} color={T.text4}
          style={{ opacity: hovered ? 1 : 0, transition: 'opacity 0.15s ease' }}
        />
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { T } = useTheme()
  const navigate = useNavigate()
  const [meetings,   setMeetings]   = useState([])
  const [stats,      setStats]      = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [query,      setQuery]      = useState('')
  const [reindexing, setReindexing] = useState(false)
  const [reindexMsg, setReindexMsg] = useState(null)

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
      value: loading ? '…' : (stats?.total_meetings ?? meetings.length),
      icon: '🎙️', color: T.blueText,   bg: T.blueBg,
    },
    {
      label: 'Decisions Found',
      value: loading ? '…' : (stats?.total_decisions ?? '—'),
      icon: '⚡', color: T.purpleText, bg: T.purpleBg,
    },
    {
      label: 'Action Items',
      value: loading ? '…' : (stats?.total_actions ?? '—'),
      icon: '✅', color: T.orangeText, bg: T.orangeBg,
    },
    {
      label: 'Topics Detected',
      value: loading ? '…' : (stats?.total_topics ?? '—'),
      icon: '🏷️', color: T.cyanText,  bg: T.cyanBg,
    },
  ]

  return (
    <div>
      {/* ── Header ── */}
      <PageHeader
        title={`${greeting()} 👋`}
        subtitle="Here's what's happening with your meetings."
        action={
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <Button
              variant="ghost"
              size="sm"
              icon={<RefreshCw size={13} />}
              loading={reindexing}
              onClick={handleReindex}
            >
              Reindex
            </Button>
            <Button
              icon={<Upload size={14} />}
              onClick={() => navigate('/upload')}
            >
              Upload Meeting
            </Button>
          </div>
        }
      />

      {/* Reindex message */}
      {reindexMsg && (
        <div className="anim-fade-in" style={{
          padding: '11px 16px', borderRadius: '10px',
          background: T.emeraldBg, border: `1px solid ${T.emerald}44`,
          fontSize: '13px', fontWeight: 600,
          color: T.emerald, marginBottom: '20px',
        }}>
          {reindexMsg}
        </div>
      )}

      {/* ── Stats grid ── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '14px', marginBottom: '32px',
      }}>
        {statCards.map((s, i) => (
          <StatCard key={s.label} delay={i * 0.06} {...s} />
        ))}
      </div>

      {/* ── Recent Meetings ── */}
      <div className="anim-fade-up anim-fade-up-3">
        <Card style={{ padding: 0, overflow: 'hidden' }}>

          {/* Card header */}
          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', gap: '16px',
            padding: '18px 20px',
            borderBottom: `1px solid ${T.border}`,
            flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
              <Mic size={16} color={T.accent} strokeWidth={2} />
              <span style={{
                fontSize: '15px', fontWeight: 700,
                color: T.text, letterSpacing: '-0.02em',
              }}>
                Recent Meetings
              </span>
              {meetings.length > 0 && (
                <span style={{
                  padding: '2px 8px', borderRadius: '99px',
                  fontSize: '11px', fontWeight: 700,
                  background: T.accentBg, color: T.accentLight,
                }}>
                  {meetings.length}
                </span>
              )}
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              {/* Search */}
              <div style={{ position: 'relative' }}>
                <Search size={13} color={T.text3} style={{
                  position: 'absolute', left: '10px',
                  top: '50%', transform: 'translateY(-50%)',
                }} />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Filter..."
                  style={{
                    padding: '7px 12px 7px 30px',
                    borderRadius: '8px', width: '160px',
                    border: `1px solid ${T.inputBorder}`,
                    background: T.inputBg,
                    color: T.text, fontSize: '13px',
                    outline: 'none',
                  }}
                  onFocus={e => e.target.style.borderColor = T.borderFocus}
                  onBlur={e => e.target.style.borderColor = T.inputBorder}
                />
              </div>
              <Button
                variant="ghost" size="sm"
                icon={<ArrowRight size={13} />}
                onClick={() => navigate('/meetings')}
              >
                View all
              </Button>
            </div>
          </div>

          {/* List */}
          <div style={{ padding: '8px 4px' }}>
            {loading ? (
              <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[1,2,3].map(i => (
                  <div key={i} style={{ display: 'flex', gap: '13px', alignItems: 'center', padding: '4px 12px' }}>
                    <Skeleton width="38px" height="38px" style={{ borderRadius: '9px', flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <Skeleton width="55%" height="14px" style={{ marginBottom: '7px' }} />
                      <Skeleton width="28%" height="11px" />
                    </div>
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <EmptyState
                icon="🎙️"
                title={query ? `No results for "${query}"` : 'No meetings yet'}
                subtitle={query ? 'Try a different search term.' : 'Upload your first meeting recording to get started.'}
                action={!query && (
                  <Button icon={<Upload size={14} />} onClick={() => navigate('/upload')}>
                    Upload Meeting
                  </Button>
                )}
              />
            ) : (
              filtered.slice(0, 7).map(m => (
                <MeetingRow
                  key={m.id}
                  meeting={m}
                  onClick={() => navigate(`/meetings/${m.id}`)}
                />
              ))
            )}
          </div>
        </Card>
      </div>

      {/* ── Quick actions ── */}
      {!loading && meetings.length > 0 && (
        <div className="anim-fade-up anim-fade-up-4" style={{ marginTop: '24px' }}>
          <div style={{
            fontSize: '11px', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: T.text3, marginBottom: '12px',
          }}>
            Quick Actions
          </div>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px',
          }}>
            {[
              { icon: <Upload size={18} color={T.blueText} />,    bg: T.blueBg,   label: 'Upload',    sub: 'New recording',    to: '/upload'    },
              { icon: <FileText size={18} color={T.purpleText} />, bg: T.purpleBg, label: 'Summaries', sub: 'AI summaries',    to: '/summaries'  },
              { icon: <CheckSquare size={18} color={T.orangeText} />, bg: T.orangeBg, label: 'Tasks', sub: 'Action items',    to: '/tasks'     },
              { icon: <BarChart2 size={18} color={T.cyanText} />,  bg: T.cyanBg,   label: 'Analytics', sub: 'Trends',         to: '/analytics'  },
            ].map(item => (
              <Card
                key={item.label} hoverable
                onClick={() => navigate(item.to)}
                style={{ padding: '18px 20px' }}
              >
                <div style={{
                  width: '38px', height: '38px', borderRadius: '9px',
                  background: item.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: '12px',
                }}>
                  {item.icon}
                </div>
                <div style={{
                  fontSize: '14px', fontWeight: 700,
                  color: T.text, letterSpacing: '-0.02em', marginBottom: '3px',
                }}>
                  {item.label}
                </div>
                <div style={{ fontSize: '12px', color: T.text3 }}>
                  {item.sub}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}