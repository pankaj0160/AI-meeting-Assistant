// client/src/pages/Analytics.jsx
// Phase 3 upgrade:
//   - Single API call instead of N+1 loop
//   - 4 real Recharts charts: AreaChart, PieChart, BarChart, LineChart
//   - Animated stat cards with count-up
//   - Premium chart styling with custom tooltips
//   - Empty state when no data yet

import { useState, useEffect } from 'react'
import {
  AreaChart, Area,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { useTheme } from '../ThemeContext'
import { getAnalytics } from '../api/client'
import { PageHeader, Card, StatCard, EmptyState, Skeleton } from '../components/ui'
import { useResponsiveGrid } from '../hooks/useResponsiveGrid'

// ── Custom Tooltip ────────────────────────────────────────────────────────────
// Recharts lets you replace the default tooltip with your own component.
// It receives active (is mouse hovering), payload (data), and label (x value).
function CustomTooltip({ active, payload, label, T }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: '12px', padding: '10px 14px',
      boxShadow: T.cardShadow, fontSize: '13px',
      fontFamily: 'var(--font)',
    }}>
      {label && <div style={{ color: T.text3, marginBottom: '6px', fontSize: '11px', fontWeight: 600 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color || p.fill }} />
          <span style={{ color: T.text2 }}>{p.name}:</span>
          <span style={{ color: T.text, fontWeight: 700 }}>{p.value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Chart card wrapper ────────────────────────────────────────────────────────
function ChartCard({ title, subtitle, children, style = {} }) {
  const { T } = useTheme()
  return (
    <Card style={{ padding: '24px', ...style }}>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '15px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>{title}</div>
        {subtitle && <div style={{ fontSize: '12px', color: T.text3, marginTop: '3px' }}>{subtitle}</div>}
      </div>
      {children}
    </Card>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Analytics() {
  const { T, isDark } = useTheme()
  const grid    = useResponsiveGrid()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // FIX: single API call instead of getMeetings + loop of getMeetingIntelligence
    getAnalytics()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) return (
    <div className="page-enter">
      <PageHeader title="Analytics" subtitle="Loading your meeting intelligence..." />
      <div style={{ display: 'grid', gridTemplateColumns: grid.cols4, gap: grid.gap, marginBottom: '28px' }}>
        {[1,2,3,4].map(i => (
          <div key={i} style={{ height: '120px', borderRadius: '18px', overflow: 'hidden' }}>
            <Skeleton width="100%" height="120px" style={{ borderRadius: '18px' }} />
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {[1,2,3,4].map(i => (
          <Card key={i} style={{ padding: '24px' }}>
            <Skeleton width="40%" height="14px" style={{ marginBottom: '20px' }} />
            <Skeleton width="100%" height="200px" />
          </Card>
        ))}
      </div>
    </div>
  )

  // ── Empty state ────────────────────────────────────────────────────────────
  if (!data || data.totals?.total_meetings === 0) return (
    <div className="page-enter">
      <PageHeader title="Analytics" subtitle="Trends and insights across all your meetings." />
      <EmptyState
        icon="📊"
        title="No data yet"
        subtitle="Process at least one meeting to start seeing analytics and trends."
      />
    </div>
  )

  const { totals, weekly_trend, task_status, top_topics, health_trend } = data

  // ── Chart data helpers ─────────────────────────────────────────────────────

  // Format weekly trend for AreaChart
  const trendData = weekly_trend.map(d => ({
    date:     new Date(d.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    meetings: d.count,
  }))

  // Format task status for PieChart
  const TASK_COLORS = {
    open:        '#3b82f6',
    in_progress: '#f97316',
    done:        '#10b981',
    overdue:     '#ef4444',
  }
  const pieData = Object.entries(task_status).map(([status, count]) => ({
    name:  status.replace('_', ' '),
    value: count,
    color: TASK_COLORS[status] || '#94a3b8',
  }))

  // Format top topics for horizontal BarChart
  const topicsData = top_topics.map(t => ({
    name:  t.title.length > 20 ? t.title.slice(0, 20) + '…' : t.title,
    count: t.count,
  }))

  // Health trend for LineChart
  const healthData = health_trend.map(h => ({
    name:  h.filename?.slice(0, 12) + '…' || h.day,
    score: h.overall_score,
  }))

  // ── Stat cards ─────────────────────────────────────────────────────────────
  const stats = [
    { label: 'Total Meetings',  value: totals.total_meetings  || 0, icon: '🎙️', color: T.accentLight, bg: isDark ? 'rgba(16,185,129,0.14)'  : 'rgba(16,185,129,0.09)',  delay: 0     },
    { label: 'Decisions Found', value: totals.total_decisions || 0, icon: '⚡',  color: T.amber, bg: isDark ? 'rgba(240,181,88,0.16)' : 'rgba(184,121,30,0.10)', delay: 0.07  },
    { label: 'Action Items',    value: totals.total_actions   || 0, icon: '✅',  color: '#fb923c', bg: isDark ? 'rgba(249,115,22,0.14)'  : 'rgba(249,115,22,0.09)',  delay: 0.14  },
    { label: 'Topics Detected', value: totals.total_topics    || 0, icon: '🏷️', color: '#22d3ee', bg: isDark ? 'rgba(6,182,212,0.14)'   : 'rgba(6,182,212,0.09)',   delay: 0.21  },
  ]

  const tooltipProps = { content: <CustomTooltip T={T} /> }
  const axisStyle   = { fontSize: 11, fill: T.text3, fontFamily: 'var(--font)' }

  return (
    <div className="page-enter">

      <PageHeader
        title="Analytics"
        eyebrow="Intelligence"
        subtitle={`Across ${totals.total_meetings} meeting${totals.total_meetings !== 1 ? 's' : ''} — ${(totals.total_decisions || 0) + (totals.total_actions || 0) + (totals.total_topics || 0)} total insights extracted`}
      />

      {/* ── Stat cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: grid.cols4, gap: grid.gap, marginBottom: '28px' }}>
        {stats.map(s => <StatCard key={s.label} {...s} />)}
      </div>

      {/* ── Charts — 2 column grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: grid.cols2, gap: grid.gap, marginBottom: '16px' }}>

        {/* Chart 1 — Meeting frequency AreaChart */}
        {/* AreaChart is like a LineChart but with the area below the line filled in.
            It shows trends much more clearly than a bar chart for time series. */}
        <ChartCard
          title="Meeting Frequency"
          subtitle="Meetings processed in the last 30 days"
        >
          {trendData.length === 0 ? (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.text3, fontSize: '13px' }}>
              No meetings in the last 30 days
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trendData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  {/* Gradient fill for the area — fades from solid to transparent */}
                  <linearGradient id="meetingGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={T.accent} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={T.accent} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                <XAxis dataKey="date" tick={axisStyle} axisLine={false} tickLine={false} />
                <YAxis tick={axisStyle} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip {...tooltipProps} />
                <Area
                  type="monotone"
                  dataKey="meetings"
                  name="Meetings"
                  stroke={T.accent}
                  strokeWidth={2.5}
                  fill="url(#meetingGrad)"
                  dot={{ fill: T.accent, strokeWidth: 0, r: 3 }}
                  activeDot={{ r: 5, fill: T.accent }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Chart 2 — Task status PieChart */}
        {/* PieChart shows proportions — perfect for status breakdown.
            Each slice has its own colour and a custom label. */}
        <ChartCard
          title="Task Status Breakdown"
          subtitle="Distribution of all action items by status"
        >
          {pieData.length === 0 ? (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.text3, fontSize: '13px' }}>
              No tasks yet
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
              <ResponsiveContainer width="55%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%" cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip {...tooltipProps} />
                </PieChart>
              </ResponsiveContainer>
              {/* Custom legend — nicer than Recharts default */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {pieData.map((d, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                    <span style={{ fontSize: '12.5px', color: T.text2, textTransform: 'capitalize' }}>{d.name}</span>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: T.text, marginLeft: 'auto', paddingLeft: '12px' }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ChartCard>

        {/* Chart 3 — Top topics horizontal BarChart */}
        {/* Horizontal bar chart is better than vertical for long category names.
            layout="vertical" swaps the axes in Recharts. */}
        <ChartCard
          title="Top Discussion Topics"
          subtitle="Most frequent topics across all meetings"
        >
          {topicsData.length === 0 ? (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.text3, fontSize: '13px' }}>
              No topics yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={topicsData}
                layout="vertical"
                margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
                barSize={14}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} horizontal={false} />
                <XAxis type="number" tick={axisStyle} axisLine={false} tickLine={false} allowDecimals={false} />
                <YAxis type="category" dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} width={100} />
                <Tooltip {...tooltipProps} />
                <Bar dataKey="count" name="Mentions" fill={T.amber} radius={[0, 5, 5, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Chart 4 — Health score trend LineChart */}
        {/* LineChart shows how a value changes over time.
            Perfect for health scores — easy to spot improving or declining trends. */}
        <ChartCard
          title="Meeting Health Trend"
          subtitle="Overall health scores across recent meetings"
        >
          {healthData.length === 0 ? (
            <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.text3, fontSize: '13px' }}>
              No health data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={healthData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="healthGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                <XAxis dataKey="name" tick={axisStyle} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={axisStyle} axisLine={false} tickLine={false} />
                <Tooltip {...tooltipProps} />
                {/* Reference lines at 60 and 80 — visual benchmarks */}
                <Line
                  type="monotone"
                  dataKey="score"
                  name="Health Score"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  dot={{ fill: '#10b981', strokeWidth: 0, r: 4 }}
                  activeDot={{ r: 6, fill: '#10b981' }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
          {/* Benchmark legend */}
          {healthData.length > 0 && (
            <div style={{ display: 'flex', gap: '16px', marginTop: '14px', paddingTop: '12px', borderTop: `1px solid ${T.border}` }}>
              {[
                { label: 'Excellent', threshold: '≥ 80', color: '#10b981' },
                { label: 'Good',      threshold: '60–79', color: '#f97316' },
                { label: 'Needs work',threshold: '< 60',  color: '#ef4444' },
              ].map(b => (
                <div key={b.label} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: b.color }} />
                  <span style={{ fontSize: '11px', color: T.text3 }}>{b.label} {b.threshold}</span>
                </div>
              ))}
            </div>
          )}
        </ChartCard>

      </div>

      {/* ── Summary row ── */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-around', flexWrap: 'wrap', gap: '20px' }}>
          {[
            {
              label: 'Avg insights per meeting',
              value: totals.total_meetings
                ? (((totals.total_decisions || 0) + (totals.total_actions || 0) + (totals.total_topics || 0)) / totals.total_meetings).toFixed(1)
                : '0',
            },
            {
              label: 'Total insights extracted',
              value: ((totals.total_decisions || 0) + (totals.total_actions || 0) + (totals.total_topics || 0)).toLocaleString(),
            },
            {
              label: 'Tasks completion rate',
              value: (() => {
                const total = Object.values(task_status).reduce((a, b) => a + b, 0)
                const done  = task_status.done || 0
                return total > 0 ? `${Math.round((done / total) * 100)}%` : '—'
              })(),
            },
            {
              label: 'Avg health score',
              value: healthData.length > 0
                ? Math.round(healthData.reduce((a, h) => a + h.score, 0) / healthData.length)
                : '—',
            },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: T.text, letterSpacing: '-0.04em' }}>{s.value}</div>
              <div style={{ fontSize: '12px', color: T.text3, fontWeight: 500, marginTop: '4px' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </Card>

    </div>
  )
}