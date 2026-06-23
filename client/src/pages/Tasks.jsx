// client/src/pages/Tasks.jsx

import { useState, useEffect, useCallback } from 'react'
import { CheckSquare } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { PageHeader, Card, Badge, EmptyState, Skeleton } from '../components/ui'
import { getTasks, updateTaskStatus } from '../api/client'

// ── Status picker ─────────────────────────────────────────────────────────────

function StatusPicker({ taskId, status, T, onUpdate }) {
  const [updating, setUpdating] = useState(false)

  const options = [
    { value: 'open',        label: 'Open',        color: T.warning, bg: T.warningBg  },
    { value: 'in_progress', label: 'In Progress',  color: T.blue,    bg: T.blueBg     },
    { value: 'done',        label: 'Done',         color: T.emerald, bg: T.emeraldBg  },
    { value: 'overdue',     label: 'Overdue',      color: T.danger,  bg: T.dangerBg   },
  ]

  const current = options.find(o => o.value === status) || options[0]

  const handleChange = async (e) => {
    const newStatus = e.target.value
    setUpdating(true)
    try {
      await updateTaskStatus(taskId, newStatus)
      onUpdate(newStatus)
    } catch {}
    finally { setUpdating(false) }
  }

  return (
    <select
      value={status}
      onChange={handleChange}
      disabled={updating || !taskId}
      style={{
        padding: '4px 10px',
        borderRadius: '99px',
        fontSize: '12px', fontWeight: 700,
        color: current.color,
        background: current.bg,
        border: `1px solid ${current.color}33`,
        cursor: taskId ? 'pointer' : 'default',
        appearance: 'none',
        outline: 'none',
        fontFamily: 'var(--font)',
        opacity: updating ? 0.6 : 1,
      }}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

// ── Priority colour helper ─────────────────────────────────────────────────────

function priorityColor(p, T) {
  if (p === 'high')  return { color: T.danger,  bg: T.dangerBg  }
  if (p === 'low')   return { color: T.emerald, bg: T.emeraldBg }
  return                    { color: T.warning, bg: T.warningBg }
}

// ── Main ───────────────────────────────────────────────────────────────────────

const FILTERS = [
  { id: 'all',  label: 'All'           },
  { id: 'open', label: 'Open'          },
  { id: 'high', label: 'High Priority' },
  { id: 'done', label: 'Done'          },
]

export default function Tasks() {
  const { T } = useTheme()

  // FIX: pagination state — same pattern as Meetings.jsx
  const [tasks,       setTasks]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [cursor,      setCursor]      = useState(null)
  const [hasMore,     setHasMore]     = useState(false)
  const [total,       setTotal]       = useState(0)
  const [filter,      setFilter]      = useState('all')

  // FIX: load first page using GET /tasks directly.
  //
  // Old code:
  //   getMeetings()              → fetches all meetings
  //   getMeetingIntelligence(id) → one call per meeting (N+1!)
  //   Only saw tasks from first 20 meetings
  //
  // New code:
  //   getTasks({ status, priority }) → one call, all tasks, paginated
  //   Uses the dedicated /tasks endpoint that already exists on the backend
  const fetchTasks = useCallback(async (activeFilter, resetList = true) => {
    if (resetList) {
      setLoading(true)
      setTasks([])
      setCursor(null)
    }

    // Map UI filter to API params
    const params = { limit: 20 }
    if (activeFilter === 'open') params.status   = 'open'
    if (activeFilter === 'done') params.status   = 'done'
    if (activeFilter === 'high') params.priority = 'high'

    try {
      const data = await getTasks(params)
      setTasks(data.items || [])
      setHasMore(data.has_more || false)
      setCursor(data.next_cursor || null)
      setTotal(data.count || 0)
    } catch {
      setTasks([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Run on mount and whenever filter changes
  useEffect(() => {
    fetchTasks(filter)
  }, [filter, fetchTasks])

  // Load next page — appends to existing list
  const loadMore = async () => {
    if (!cursor || loadingMore) return
    setLoadingMore(true)

    const params = { limit: 20, cursor }
    if (filter === 'open') params.status   = 'open'
    if (filter === 'done') params.status   = 'done'
    if (filter === 'high') params.priority = 'high'

    try {
      const data = await getTasks(params)
      setTasks(prev => [...prev, ...(data.items || [])])
      setHasMore(data.has_more || false)
      setCursor(data.next_cursor || null)
    } catch {}
    finally { setLoadingMore(false) }
  }

  // Update a task's status in local state without refetching
  const handleStatusUpdate = (taskId, newStatus) => {
    setTasks(prev => prev.map(t =>
      t.id === taskId ? { ...t, status: newStatus } : t
    ))
  }

  return (
    <div>
      <PageHeader
        title="Action Items"
        subtitle={`${tasks.length} task${tasks.length !== 1 ? 's' : ''} loaded`}
      />

      {/* ── Filter pills ── */}
      <div style={{
        display: 'flex', gap: '8px',
        marginBottom: '24px', flexWrap: 'wrap',
      }}>
        {FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            style={{
              padding: '7px 16px', borderRadius: '99px',
              fontSize: '13px', fontWeight: 600,
              color:      filter === f.id ? T.navActiveText : T.text3,
              background: filter === f.id ? T.navActiveBg   : T.surface,
              border: `1px solid ${filter === f.id ? T.navActiveBorder : T.border}`,
              cursor: 'pointer', transition: 'all 0.15s ease',
              fontFamily: 'var(--font)',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Task list ── */}
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          // Skeleton loading state — 5 placeholder rows
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {[1,2,3,4,5].map(i => (
              <div key={i} style={{ padding: '4px 8px' }}>
                <Skeleton width="65%" height="15px" style={{ marginBottom: '8px' }} />
                <Skeleton width="35%" height="12px" />
              </div>
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <EmptyState
            icon="✅"
            title="No tasks found"
            subtitle={
              filter !== 'all'
                ? `No ${filter} tasks. Try a different filter.`
                : 'Process a meeting to extract action items automatically.'
            }
          />
        ) : (
          <div>
            {/* Table header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 160px 100px 120px',
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

            {/* Task rows */}
            {tasks.map((task, i) => {
              const pc = priorityColor(task.priority, T)
              return (
                <div
                  key={task.id || i}
                  className="anim-fade-up"
                  style={{ animationDelay: `${i * 0.03}s` }}
                >
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 160px 100px 120px',
                      gap: '16px', padding: '16px 24px',
                      alignItems: 'center',
                      borderBottom: `1px solid ${T.border}`,
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = T.surfaceHover}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    {/* Task text + meta */}
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

                    {/* Meeting name — from meeting_filename field in paginated response */}
                    <div style={{
                      fontSize: '12px', color: T.text3,
                      fontWeight: 500,
                      whiteSpace: 'nowrap', overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {(task.meeting_filename || task.meetingName || 'Meeting').slice(0, 22)}
                    </div>

                    {/* Priority badge */}
                    <div>
                      <Badge color={pc.color} bg={pc.bg}>
                        {task.priority || 'medium'}
                      </Badge>
                    </div>

                    {/* Status picker */}
                    <div>
                      <StatusPicker
                        taskId={task.id}
                        status={task.status || 'open'}
                        T={T}
                        onUpdate={(newStatus) => handleStatusUpdate(task.id, newStatus)}
                      />
                    </div>
                  </div>
                </div>
              )
            })}

            {/* FIX: Load more button */}
            {hasMore && (
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
                  {loadingMore ? 'Loading...' : 'Load more tasks'}
                </button>
              </div>
            )}

            {/* All loaded indicator */}
            {!hasMore && tasks.length > 0 && (
              <div style={{
                padding: '16px 24px',
                textAlign: 'center',
                fontSize: '12px',
                color: T.text3,
                borderTop: `1px solid ${T.border}`,
              }}>
                All {tasks.length} tasks loaded
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}