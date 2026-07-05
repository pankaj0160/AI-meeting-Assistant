// client/src/pages/Tasks.jsx
// Phase 3 upgrade:
//   - Kanban board view (drag-and-drop columns)
//   - Toggle between List and Kanban view
//   - View preference saved to localStorage
//   - All pagination + N+1 fixes from previous phase preserved

import { useState, useEffect, useCallback, useRef } from 'react'
import { LayoutList, Columns, CheckSquare } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { PageHeader, Card, Badge, EmptyState, Skeleton, Button } from '../components/ui'
import { getTasks, updateTaskStatus } from '../api/client'
import { useToast } from '../components/Toast'

// ── Constants ─────────────────────────────────────────────────────────────────

// Kanban column definitions — each maps to a task status value
const COLUMNS = [
  {
    id:       'open',
    label:    'Open',
    icon:     '🔵',
    color:    '#3b82f6',
    bg:       'rgba(59,130,246,0.10)',
    border:   'rgba(59,130,246,0.25)',
  },
  {
    id:       'in_progress',
    label:    'In Progress',
    icon:     '🟡',
    color:    '#f97316',
    bg:       'rgba(249,115,22,0.10)',
    border:   'rgba(249,115,22,0.25)',
  },
  {
    id:       'done',
    label:    'Done',
    icon:     '🟢',
    color:    '#10b981',
    bg:       'rgba(16,185,129,0.10)',
    border:   'rgba(16,185,129,0.25)',
  },
]

const LIST_FILTERS = [
  { id: 'all',  label: 'All'           },
  { id: 'open', label: 'Open'          },
  { id: 'high', label: 'High Priority' },
  { id: 'done', label: 'Done'          },
]

// ── Priority colour helper ─────────────────────────────────────────────────────
function priorityColor(p, T) {
  if (p === 'high') return { color: T.danger,  bg: T.dangerBg  }
  if (p === 'low')  return { color: T.emerald, bg: T.emeraldBg }
  return                   { color: T.warning, bg: T.warningBg }
}

// ── Kanban Task Card ──────────────────────────────────────────────────────────
// draggable="true" — makes this card draggable
// onDragStart     — stores task id so the column knows what was dropped
function KanbanCard({ task, T, isDark, onDragStart }) {
  const [hov, setHov] = useState(false)
  const pc = priorityColor(task.priority, T)

  return (
    <div
      draggable="true"
      onDragStart={() => onDragStart(task.id)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '13px 14px',
        borderRadius: '12px',
        background: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
        border: `1px solid ${hov ? T.border2 : T.border}`,
        cursor: 'grab',
        transition: 'all 0.15s var(--ease)',
        transform: hov ? 'translateY(-1px)' : 'translateY(0)',
        boxShadow: hov ? T.cardShadow : 'none',
        userSelect: 'none',    // prevent text selection while dragging
      }}
    >
      {/* Task text */}
      <div style={{
        fontSize: '13px', fontWeight: 600,
        color: T.text, lineHeight: 1.5,
        marginBottom: '10px',
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      }}>
        {task.task}
      </div>

      {/* Meta row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
        {task.owner && (
          <span style={{
            fontSize: '11px', color: T.text3,
            display: 'flex', alignItems: 'center', gap: '3px',
          }}>
            👤 {task.owner}
          </span>
        )}
        {task.deadline && (
          <span style={{ fontSize: '11px', color: T.text3 }}>
            📅 {task.deadline}
          </span>
        )}
      </div>

      {/* Footer: meeting name + priority badge */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: '8px',
      }}>
        <div style={{
          fontSize: '11px', color: T.text3,
          fontWeight: 500, flex: 1, minWidth: 0,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          🎙️ {(task.meeting_filename || 'Meeting').slice(0, 18)}
        </div>
        <Badge color={pc.color} bg={pc.bg}>
          {task.priority || 'medium'}
        </Badge>
      </div>
    </div>
  )
}

// ── Kanban Column ─────────────────────────────────────────────────────────────
// onDragOver: must call e.preventDefault() to tell browser "dropping is allowed here"
// onDrop:     fires when user releases the drag — we call onDrop(columnId)
function KanbanColumn({ col, tasks, T, isDark, onDragStart, onDrop }) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = (e) => {
    // IMPORTANT: without this, onDrop never fires
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => setIsDragOver(false)

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    onDrop(col.id)
  }

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        flex: '1 1 0',
        minWidth: '240px',
        display: 'flex',
        flexDirection: 'column',
        gap: '0',
        borderRadius: '16px',
        // Highlight the column when a card is being dragged over it
        border: `1.5px solid ${isDragOver ? col.color : T.border}`,
        background: isDragOver ? col.bg : T.surface,
        transition: 'all 0.15s var(--ease)',
        overflow: 'hidden',
      }}
    >
      {/* Column header */}
      <div style={{
        padding: '14px 16px',
        borderBottom: `1px solid ${T.border}`,
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        background: isDragOver ? col.bg : 'transparent',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px' }}>{col.icon}</span>
          <span style={{
            fontSize: '13px', fontWeight: 700,
            color: isDragOver ? col.color : T.text,
            transition: 'color 0.15s',
          }}>
            {col.label}
          </span>
        </div>
        {/* Task count badge */}
        <span style={{
          padding: '2px 8px', borderRadius: '99px',
          fontSize: '11px', fontWeight: 700,
          color: col.color,
          background: col.bg,
          border: `1px solid ${col.border}`,
          minWidth: '24px', textAlign: 'center',
        }}>
          {tasks.length}
        </span>
      </div>

      {/* Cards */}
      <div style={{
        flex: 1,
        padding: '10px',
        display: 'flex', flexDirection: 'column',
        gap: '8px',
        minHeight: '120px',  // always visible as a drop zone even when empty
        overflowY: 'auto',
        maxHeight: 'calc(100vh - 320px)',
      }}>
        {tasks.length === 0 ? (
          // Empty column drop zone — visual hint
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center',
            justifyContent: 'center',
            fontSize: '12px', color: T.text3,
            border: `1.5px dashed ${isDragOver ? col.color : T.border}`,
            borderRadius: '10px', padding: '24px',
            transition: 'all 0.15s',
          }}>
            {isDragOver ? `Drop here` : `No ${col.label.toLowerCase()} tasks`}
          </div>
        ) : (
          tasks.map((task, i) => (
            <div
              key={task.id || i}
              className="anim-fade-up"
              style={{ animationDelay: `${i * 0.04}s` }}
            >
              <KanbanCard
                task={task}
                T={T}
                isDark={isDark}
                onDragStart={onDragStart}
              />
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Kanban Board ──────────────────────────────────────────────────────────────
function KanbanBoard({ tasks, T, isDark, onStatusChange }) {
  // draggingId: the task.id of the card currently being dragged
  // stored in a ref (not state) because we don't need a re-render when it changes
  const draggingId = useRef(null)

  const handleDragStart = (taskId) => {
    draggingId.current = taskId
  }

  const handleDrop = (newStatus) => {
    if (!draggingId.current) return
    const task = tasks.find(t => t.id === draggingId.current)
    if (!task || task.status === newStatus) {
      draggingId.current = null
      return
    }
    // Notify parent to update status via API
    onStatusChange(draggingId.current, newStatus)
    draggingId.current = null
  }

  // Split all tasks into their respective columns
  const tasksByColumn = COLUMNS.reduce((acc, col) => {
    acc[col.id] = tasks.filter(t =>
      // 'open' column also shows tasks with no status set
      col.id === 'open'
        ? (!t.status || t.status === 'open')
        : t.status === col.id
    )
    return acc
  }, {})

  return (
    <div style={{
      display: 'flex',
      gap: '16px',
      alignItems: 'flex-start',
      overflowX: 'auto',
      paddingBottom: '8px',
    }}>
      {COLUMNS.map(col => (
        <KanbanColumn
          key={col.id}
          col={col}
          tasks={tasksByColumn[col.id] || []}
          T={T}
          isDark={isDark}
          onDragStart={handleDragStart}
          onDrop={handleDrop}
        />
      ))}
    </div>
  )
}

// ── List View (unchanged from previous fix) ───────────────────────────────────
function ListView({ tasks, T, loading, loadingMore, hasMore, filter, onStatusUpdate, onLoadMore, onFilterChange }) {
  return (
    <>
      {/* Filter pills */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap' }}>
        {LIST_FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => onFilterChange(f.id)}
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
        ) : tasks.length === 0 ? (
          <EmptyState
            icon="✅"
            title="No tasks found"
            subtitle={filter !== 'all' ? `No ${filter} tasks. Try a different filter.` : 'Process a meeting to extract action items automatically.'}
          />
        ) : (
          <div>
            {/* Table header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 160px 100px 120px',
              gap: '16px', padding: '12px 24px',
              borderBottom: `1px solid ${T.border}`,
            }}>
              {['Task', 'Meeting', 'Priority', 'Status'].map(h => (
                <div key={h} style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: T.text3 }}>
                  {h}
                </div>
              ))}
            </div>

            {/* Rows */}
            {tasks.map((task, i) => {
              const pc = priorityColor(task.priority, T)
              return (
                <div key={task.id || i} className="anim-fade-up" style={{ animationDelay: `${i * 0.03}s` }}>
                  <div
                    style={{
                      display: 'grid', gridTemplateColumns: '1fr 160px 100px 120px',
                      gap: '16px', padding: '16px 24px', alignItems: 'center',
                      borderBottom: `1px solid ${T.border}`,
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = T.surfaceHover}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: T.text, marginBottom: '4px' }}>{task.task}</div>
                      <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: T.text3, flexWrap: 'wrap' }}>
                        {task.owner    && <span>👤 {task.owner}</span>}
                        {task.deadline && <span>📅 {task.deadline}</span>}
                      </div>
                    </div>
                    <div style={{ fontSize: '12px', color: T.text3, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {(task.meeting_filename || 'Meeting').slice(0, 22)}
                    </div>
                    <div><Badge color={pc.color} bg={pc.bg}>{task.priority || 'medium'}</Badge></div>
                    <div>
                      <StatusPicker taskId={task.id} status={task.status || 'open'} T={T} onUpdate={(s) => onStatusUpdate(task.id, s)} />
                    </div>
                  </div>
                </div>
              )
            })}

            {/* Load more */}
            {hasMore && (
              <div style={{ padding: '20px 24px', borderTop: `1px solid ${T.border}` }}>
                <button onClick={onLoadMore} disabled={loadingMore}
                  style={{ width: '100%', padding: '10px', borderRadius: '10px', border: `1px solid ${T.border}`, background: T.surface, color: T.text2, fontSize: '13.5px', fontWeight: 500, cursor: loadingMore ? 'not-allowed' : 'pointer', opacity: loadingMore ? 0.6 : 1, fontFamily: 'var(--font)' }}
                >
                  {loadingMore ? 'Loading...' : 'Load more tasks'}
                </button>
              </div>
            )}
            {!hasMore && tasks.length > 0 && (
              <div style={{ padding: '16px', textAlign: 'center', fontSize: '12px', color: T.text3, borderTop: `1px solid ${T.border}` }}>
                All {tasks.length} tasks loaded
              </div>
            )}
          </div>
        )}
      </Card>
    </>
  )
}

// ── Status Picker (used in List view) ─────────────────────────────────────────
function StatusPicker({ taskId, status, T, onUpdate }) {
  const [updating, setUpdating] = useState(false)

  const options = [
    { value: 'open',        label: 'Open',        color: T.warning, bg: T.warningBg  },
    { value: 'in_progress', label: 'In Progress',  color: '#3b82f6', bg: T.blueBg     },
    { value: 'done',        label: 'Done',         color: T.emerald, bg: T.emeraldBg  },
    { value: 'overdue',     label: 'Overdue',      color: T.danger,  bg: T.dangerBg   },
  ]

  const current = options.find(o => o.value === status) || options[0]

  return (
    <select
      value={status}
      onChange={async (e) => {
        setUpdating(true)
        try { await updateTaskStatus(taskId, e.target.value); onUpdate(e.target.value) } catch {}
        finally { setUpdating(false) }
      }}
      disabled={updating}
      style={{
        padding: '4px 10px', borderRadius: '99px',
        fontSize: '12px', fontWeight: 700,
        color: current.color, background: current.bg,
        border: `1px solid ${current.color}33`,
        cursor: 'pointer', appearance: 'none', outline: 'none',
        fontFamily: 'var(--font)', opacity: updating ? 0.6 : 1,
      }}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Tasks() {
  const { T, isDark } = useTheme()
  const { toast }     = useToast()

  // FIX: view preference persisted in localStorage
  // so the user's choice is remembered across page refreshes
  const [view,        setView]        = useState(() => localStorage.getItem('tasks_view') || 'list')
  const [tasks,       setTasks]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [cursor,      setCursor]      = useState(null)
  const [hasMore,     setHasMore]     = useState(false)
  const [filter,      setFilter]      = useState('all')

  const switchView = (v) => {
    setView(v)
    localStorage.setItem('tasks_view', v)
  }

  const fetchTasks = useCallback(async (activeFilter, reset = true) => {
    if (reset) { setLoading(true); setTasks([]); setCursor(null) }
    const params = { limit: 50 }     // kanban needs more at once — load 50
    if (activeFilter === 'open') params.status   = 'open'
    if (activeFilter === 'done') params.status   = 'done'
    if (activeFilter === 'high') params.priority = 'high'
    try {
      const data = await getTasks(params)
      setTasks(data.items || [])
      setHasMore(data.has_more || false)
      setCursor(data.next_cursor || null)
    } catch { setTasks([]) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchTasks(filter) }, [filter, fetchTasks])

  const loadMore = async () => {
    if (!cursor || loadingMore) return
    setLoadingMore(true)
    const params = { limit: 50, cursor }
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

  // Update status in local state — no refetch needed
  const handleStatusUpdate = (taskId, newStatus) => {
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t))
  }

  // Kanban drag-drop status change
  // Uses optimistic update: change local state immediately,
  // then call API in background — if API fails, revert + show toast
  const handleKanbanStatusChange = async (taskId, newStatus) => {
    // Optimistic update — update local state immediately for instant visual feedback
    // The user sees the card move before the API call completes
    const original = tasks.find(t => t.id === taskId)?.status
    handleStatusUpdate(taskId, newStatus)

    try {
      await updateTaskStatus(taskId, newStatus)
      toast.success('Task updated', `Moved to ${newStatus.replace('_', ' ')}`)
    } catch {
      // Revert on failure — put the card back where it was
      handleStatusUpdate(taskId, original)
      toast.error('Update failed', 'Could not move the task. Please try again.')
    }
  }

  // Open/Done counts for the header
  const openCount = tasks.filter(t => !t.status || t.status === 'open').length
  const doneCount = tasks.filter(t => t.status === 'done').length

  return (
    <div className="page-enter">

      {/* ── Header with view toggle ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', color: T.accent, marginBottom: '6px' }}>
            Tasks
          </div>
          <h1 style={{ fontSize: '32px', fontWeight: 800, letterSpacing: '-0.05em', color: T.text, margin: 0, lineHeight: 1.1 }}>
            Action Items
          </h1>
          {!loading && (
            <p style={{ fontSize: '14px', color: T.text3, margin: '8px 0 0', lineHeight: 1.6 }}>
              {openCount} open · {doneCount} done · {tasks.length} total
            </p>
          )}
        </div>

        {/* View toggle — List or Kanban */}
        {/* This is a controlled toggle: clicking a button sets view state,
            which determines which component renders below */}
        <div style={{
          display: 'flex', gap: '4px', padding: '4px',
          background: T.surface2, borderRadius: '12px',
          border: `1px solid ${T.border}`,
          height: 'fit-content',
        }}>
          {[
            { id: 'list',   icon: <LayoutList size={15} />,  label: 'List'   },
            { id: 'kanban', icon: <Columns    size={15} />,  label: 'Kanban' },
          ].map(v => (
            <button
              key={v.id}
              onClick={() => switchView(v.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '7px 14px', borderRadius: '9px',
                border: view === v.id ? `1px solid ${T.border2}` : '1px solid transparent',
                background: view === v.id ? T.surface : 'transparent',
                color: view === v.id ? T.text : T.text3,
                fontSize: '13px', fontWeight: 600,
                cursor: 'pointer',
                transition: 'all var(--speed-fast) var(--ease)',
                boxShadow: view === v.id ? T.cardShadow : 'none',
                fontFamily: 'inherit',
              }}
            >
              {v.icon} {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Kanban loading skeleton ── */}
      {loading && view === 'kanban' && (
        <div style={{ display: 'flex', gap: '16px' }}>
          {COLUMNS.map(col => (
            <div key={col.id} style={{ flex: '1 1 0', borderRadius: '16px', border: `1px solid ${T.border}`, overflow: 'hidden', background: T.surface }}>
              <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>{col.icon}</span>
                <Skeleton width="60px" height="14px" />
              </div>
              <div style={{ padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {[1,2,3].map(i => (
                  <div key={i} style={{ padding: '13px 14px', borderRadius: '12px', border: `1px solid ${T.border}` }}>
                    <Skeleton width="85%" height="13px" style={{ marginBottom: '8px' }} />
                    <Skeleton width="50%" height="11px" style={{ marginBottom: '10px' }} />
                    <Skeleton width="40%" height="20px" style={{ borderRadius: '99px' }} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Kanban Board ── */}
      {!loading && view === 'kanban' && (
        <>
          {tasks.length === 0 ? (
            <EmptyState
              icon="🗂️"
              title="No tasks yet"
              subtitle="Process a meeting to automatically extract action items."
            />
          ) : (
            <>
              {/* Kanban tip */}
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: '7px',
                padding: '5px 12px', borderRadius: '99px', marginBottom: '16px',
                background: T.surface2, border: `1px solid ${T.border}`,
                fontSize: '11.5px', color: T.text3,
              }}>
                <span>💡</span> Drag cards between columns to update status
              </div>
              <KanbanBoard
                tasks={tasks}
                T={T}
                isDark={isDark}
                onStatusChange={handleKanbanStatusChange}
              />
            </>
          )}
        </>
      )}

      {/* ── List View ── */}
      {view === 'list' && (
        <ListView
          tasks={tasks}
          T={T}
          loading={loading}
          loadingMore={loadingMore}
          hasMore={hasMore}
          filter={filter}
          onStatusUpdate={handleStatusUpdate}
          onLoadMore={loadMore}
          onFilterChange={(f) => { setFilter(f); fetchTasks(f) }}
        />
      )}

    </div>
  )
}