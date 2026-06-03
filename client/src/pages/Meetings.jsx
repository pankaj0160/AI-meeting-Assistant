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
  const [meetings, setMeetings] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [query,    setQuery]    = useState('')

  useEffect(() => {
    getMeetings()
      .then(setMeetings)
      .catch(() => setMeetings([]))
      .finally(() => setLoading(false))
  }, [])

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

      {/* ── Search ── */}
      <div style={{ position: 'relative', marginBottom: '24px', maxWidth: '420px' }}>
        <Search
          size={16} color={T.text3}
          style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }}
        />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search meetings..."
          style={{
            width: '100%',
            padding: '11px 16px 11px 42px',
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

      {/* ── List ── */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[1,2,3,4].map(i => (
              <div key={i} style={{ display: 'flex', gap: '14px', alignItems: 'center', padding: '8px 4px' }}>
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
            {/* Table header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 160px 120px 44px',
              gap: '16px',
              padding: '12px 24px',
              borderBottom: `1px solid ${T.border}`,
            }}>
              {['Meeting', 'Date', 'Status', ''].map(h => (
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
          gridTemplateColumns: '1fr 160px 120px 44px',
          gap: '16px',
          padding: '16px 24px',
          alignItems: 'center',
          cursor: 'pointer',
          background: hovered ? T.surfaceHover : 'transparent',
          borderBottom: `1px solid ${T.border}`,
          transition: 'background 0.15s ease',
        }}
      >
        {/* Name */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0 }}>
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

        {/* Date */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '7px',
          fontSize: '13px', color: T.text3, fontWeight: 400,
        }}>
          <Calendar size={13} color={T.text4} />
          {fmt(meeting.created_at)}
        </div>

        {/* Status */}
        <div>
          <Badge color={T.emeraldText} bg={T.emeraldBg}>
            Processed
          </Badge>
        </div>

        {/* Arrow */}
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