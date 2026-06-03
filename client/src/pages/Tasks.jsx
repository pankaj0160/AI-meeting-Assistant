// client/src/pages/Tasks.jsx

import { useState, useEffect } from 'react'
import { CheckSquare, Filter } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeetings, getMeetingIntelligence } from '../api/client'
import { PageHeader, Card, Badge, EmptyState, Skeleton, SectionLabel } from '../components/ui'

export default function Tasks() {
  const { T } = useTheme()
  const [tasks,    setTasks]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [filter,   setFilter]   = useState('all') // 'all' | 'open' | 'high'

  useEffect(() => {
    async function load() {
      try {
        const meetings = await getMeetings()
        const all = []
        await Promise.all(
          meetings.slice(0, 20).map(async m => {
            try {
              const intel = await getMeetingIntelligence(m.id)
              if (intel?.action_items) {
                intel.action_items.forEach(item => {
                  all.push({ ...item, meetingId: m.id, meetingName: m.filename })
                })
              }
            } catch {}
          })
        )
        setTasks(all)
      } catch {}
      finally { setLoading(false) }
    }
    load()
  }, [])

  const filtered = tasks.filter(t => {
    if (filter === 'open')   return (t.status || 'open') === 'open'
    if (filter === 'high')   return t.priority === 'high'
    return true
  })

  const priorityColor = p => {
    if (p === 'high')   return { color: T.danger,   bg: T.dangerBg }
    if (p === 'low')    return { color: T.emerald,  bg: T.emeraldBg }
    return { color: T.warning, bg: T.warningBg }
  }

  return (
    <div>
      <PageHeader
        title="Action Items"
        subtitle={`${tasks.length} tasks across all meetings`}
      />

      {/* ── Filters ── */}
      <div style={{
        display: 'flex', gap: '8px', marginBottom: '24px',
        flexWrap: 'wrap',
      }}>
        {[
          { id: 'all',  label: `All (${tasks.length})` },
          { id: 'open', label: 'Open' },
          { id: 'high', label: 'High Priority' },
        ].map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            style={{
              padding: '7px 16px', borderRadius: '99px',
              fontSize: '13px', fontWeight: 600,
              color: filter === f.id ? T.navActiveText : T.text3,
              background: filter === f.id ? T.navActiveBg : T.surface,
              border: `1px solid ${filter === f.id ? T.navActiveBorder : T.border}`,
              cursor: 'pointer', transition: 'all 0.15s ease',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[1,2,3,4,5].map(i => (
              <div key={i} style={{ padding: '4px 8px' }}>
                <Skeleton width="65%" height="15px" style={{ marginBottom: '8px' }} />
                <Skeleton width="35%" height="12px" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="✅"
            title="No tasks found"
            subtitle="Process a meeting to extract action items automatically."
          />
        ) : (
          <div>
            {/* Header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 140px 100px 100px',
              gap: '16px', padding: '12px 24px',
              borderBottom: `1px solid ${T.border}`,
            }}>
              {['Task', 'Meeting', 'Priority', 'Status'].map(h => (
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
            {filtered.map((task, i) => {
              const pc = priorityColor(task.priority)
              return (
                <div
                  key={i}
                  className="anim-fade-up"
                  style={{ animationDelay: `${i * 0.03}s` }}
                >
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 140px 100px 100px',
                    gap: '16px', padding: '16px 24px',
                    alignItems: 'center',
                    borderBottom: `1px solid ${T.border}`,
                    transition: 'background 0.15s ease',
                  }}
                    onMouseEnter={e => e.currentTarget.style.background = T.surfaceHover}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div>
                      <div style={{
                        fontSize: '14px', fontWeight: 600,
                        color: T.text, marginBottom: '4px',
                        letterSpacing: '-0.01em',
                      }}>
                        {task.task}
                      </div>
                      <div style={{
                        display: 'flex', gap: '12px',
                        fontSize: '12px', color: T.text3,
                        flexWrap: 'wrap',
                      }}>
                        {task.owner    && <span>👤 {task.owner}</span>}
                        {task.deadline && <span>📅 {task.deadline}</span>}
                      </div>
                    </div>
                    <div style={{
                      fontSize: '12px', color: T.text3,
                      fontWeight: 500,
                      whiteSpace: 'nowrap', overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {(task.meetingName || 'Meeting').slice(0, 20)}
                    </div>
                    <div>
                      <Badge color={pc.color} bg={pc.bg}>
                        {task.priority || 'medium'}
                      </Badge>
                    </div>
                    <div>
                      <Badge
                        color={task.status === 'open' ? T.warning : T.emerald}
                        bg={task.status === 'open' ? T.warningBg : T.emeraldBg}
                      >
                        {task.status || 'open'}
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