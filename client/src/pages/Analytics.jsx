// client/src/pages/Analytics.jsx

import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, LineChart, Line
} from 'recharts'
import { useTheme } from '../ThemeContext'
import { getMeetings, getMeetingIntelligence } from '../api/client'
import { PageHeader, Card, StatCard, SectionLabel, EmptyState, Skeleton } from '../components/ui'

export default function Analytics() {
  const { T } = useTheme()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const meetings = await getMeetings()
        let totalDecisions = 0
        let totalActions   = 0
        let totalTopics    = 0

        const weekMap = {}

        await Promise.all(
          meetings.slice(0, 20).map(async m => {
            try {
              const intel = await getMeetingIntelligence(m.id)
              if (intel) {
                totalDecisions += intel.decisions?.length   || 0
                totalActions   += intel.action_items?.length || 0
                totalTopics    += intel.topics?.length      || 0
              }
              // Group by week
              const week = m.created_at
                ? new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : 'Unknown'
              weekMap[week] = (weekMap[week] || 0) + 1
            } catch {}
          })
        )

        const weeklyData = Object.entries(weekMap)
          .slice(-8)
          .map(([date, count]) => ({ date, meetings: count }))

        setData({
          total: meetings.length,
          decisions: totalDecisions,
          actions: totalActions,
          topics: totalTopics,
          weeklyData,
          meetings,
        })
      } catch {}
      finally { setLoading(false) }
    }
    load()
  }, [])

  const tooltipStyle = {
    backgroundColor: T.surface,
    border: `1px solid ${T.border}`,
    borderRadius: '10px',
    color: T.text,
    fontSize: '13px',
    fontFamily: 'var(--font)',
    boxShadow: T.cardShadow,
  }

  if (loading) return (
    <div>
      <PageHeader title="Analytics" subtitle="Loading data..." />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
        {[1,2,3,4].map(i => (
          <Card key={i}>
            <Skeleton width="60%" height="12px" style={{ marginBottom: '16px' }} />
            <Skeleton width="40%" height="36px" />
          </Card>
        ))}
      </div>
    </div>
  )

  if (!data) return (
    <EmptyState icon="📊" title="No data yet" subtitle="Process some meetings to see analytics." />
  )

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Trends and insights across all your meetings."
      />

      {/* ── Stats ── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px', marginBottom: '32px',
      }}>
        <StatCard label="Total Meetings"  value={data.total}     icon="🎙️" color={T.blueText}   bg={T.blueBg}   delay={0}    />
        <StatCard label="Decisions Found" value={data.decisions} icon="⚡"  color={T.purpleText} bg={T.purpleBg} delay={0.06} />
        <StatCard label="Action Items"    value={data.actions}   icon="✅"  color={T.orangeText} bg={T.orangeBg} delay={0.12} />
        <StatCard label="Topics Detected" value={data.topics}    icon="🏷️" color={T.cyanText}   bg={T.cyanBg}   delay={0.18} />
      </div>

      {/* ── Charts ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>

        {/* Meetings per day */}
        <div className="anim-fade-up anim-fade-up-3">
          <Card>
            <div style={{
              fontSize: '16px', fontWeight: 700,
              letterSpacing: '-0.03em', color: T.text,
              marginBottom: '24px',
            }}>
              Meetings Over Time
            </div>
            {data.weeklyData.length === 0 ? (
              <div style={{ fontSize: '14px', color: T.text3, padding: '32px 0', textAlign: 'center' }}>
                Not enough data yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.weeklyData} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: T.text3, fontFamily: 'var(--font)' }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: T.text3, fontFamily: 'var(--font)' }}
                    axisLine={false} tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    cursor={{ fill: T.accentBg }}
                  />
                  <Bar dataKey="meetings" fill={T.accent} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        {/* Intelligence breakdown */}
        <div className="anim-fade-up anim-fade-up-4">
          <Card>
            <div style={{
              fontSize: '16px', fontWeight: 700,
              letterSpacing: '-0.03em', color: T.text,
              marginBottom: '24px',
            }}>
              Intelligence Breakdown
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {[
                { label: 'Decisions',    value: data.decisions, total: Math.max(data.decisions, 1), color: T.purple },
                { label: 'Action Items', value: data.actions,   total: Math.max(data.actions, 1),   color: T.orange },
                { label: 'Topics',       value: data.topics,    total: Math.max(data.topics, 1),    color: T.cyan   },
              ].map(item => (
                <div key={item.label}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    marginBottom: '7px',
                  }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: T.text2 }}>
                      {item.label}
                    </span>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: T.text }}>
                      {item.value}
                    </span>
                  </div>
                  <div style={{
                    height: '8px', borderRadius: '99px',
                    background: T.surface2, overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, (item.value / Math.max(data.decisions, data.actions, data.topics, 1)) * 100)}%`,
                      background: item.color,
                      borderRadius: '99px',
                      transition: 'width 0.8s ease',
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

      </div>
    </div>
  )
}