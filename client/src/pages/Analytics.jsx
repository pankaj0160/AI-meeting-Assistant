// client/src/pages/Analytics.jsx

import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { useTheme } from '../ThemeContext'
import { getMeetings, getMeetingIntelligence } from '../api/client'
import { PageHeader, Card, StatCard, EmptyState, Skeleton } from '../components/ui'

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
                totalDecisions += intel.decisions?.length    || 0
                totalActions   += intel.action_items?.length || 0
                totalTopics    += intel.topics?.length       || 0
              }
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

        setData({ total: meetings.length, decisions: totalDecisions, actions: totalActions, topics: totalTopics, weeklyData })
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
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <PageHeader title="Analytics" subtitle="Loading data..." />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '14px', marginBottom: '28px' }}>
        {[1,2,3,4].map(i => (
          <Card key={i} style={{ padding: '20px' }}>
            <Skeleton width="55%" height="11px" style={{ marginBottom: '14px' }} />
            <Skeleton width="35%" height="32px" />
          </Card>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {[1,2].map(i => (
          <Card key={i} style={{ padding: '24px' }}>
            <Skeleton width="40%" height="14px" style={{ marginBottom: '20px' }} />
            <Skeleton width="100%" height="180px" />
          </Card>
        ))}
      </div>
    </div>
  )

  if (!data) return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
      <EmptyState icon="📊" title="No data yet" subtitle="Process some meetings to see analytics." />
    </div>
  )

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto' }}>

      <PageHeader
        title="Analytics"
        subtitle="Trends and insights across all your meetings."
      />

      {/* ── Stats row ── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '14px',
        marginBottom: '28px',
      }}>
        <StatCard label="Total Meetings"  value={data.total}     icon="🎙️" color={T.blueText}   bg={T.blueBg}   delay={0}    />
        <StatCard label="Decisions Found" value={data.decisions} icon="⚡"  color={T.purpleText} bg={T.purpleBg} delay={0.06} />
        <StatCard label="Action Items"    value={data.actions}   icon="✅"  color={T.orangeText} bg={T.orangeBg} delay={0.12} />
        <StatCard label="Topics Detected" value={data.topics}    icon="🏷️" color={T.cyanText}   bg={T.cyanBg}   delay={0.18} />
      </div>

      {/* ── Charts row ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

        {/* Meetings over time */}
        <Card style={{ padding: '24px' }}>
          <div style={{
            fontSize: '14px', fontWeight: 700,
            color: T.text, letterSpacing: '-0.02em',
            marginBottom: '20px',
          }}>
            Meetings Over Time
          </div>
          {data.weeklyData.length === 0 ? (
            <div style={{
              height: '180px', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              fontSize: '13px', color: T.text3,
            }}>
              Not enough data yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={data.weeklyData} barSize={24}>
                <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: T.text3, fontFamily: 'var(--font)' }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: T.text3, fontFamily: 'var(--font)' }}
                  axisLine={false} tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: T.accentBg }} />
                <Bar dataKey="meetings" fill={T.accent} radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Intelligence breakdown */}
        <Card style={{ padding: '24px' }}>
          <div style={{
            fontSize: '14px', fontWeight: 700,
            color: T.text, letterSpacing: '-0.02em',
            marginBottom: '20px',
          }}>
            Intelligence Breakdown
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', marginTop: '8px' }}>
            {[
              { label: 'Decisions',    value: data.decisions, color: T.purple },
              { label: 'Action Items', value: data.actions,   color: T.orange },
              { label: 'Topics',       value: data.topics,    color: T.cyan   },
            ].map(item => {
              const max = Math.max(data.decisions, data.actions, data.topics, 1)
              return (
                <div key={item.label}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: '8px',
                  }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: T.text2 }}>
                      {item.label}
                    </span>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: T.text }}>
                      {item.value}
                    </span>
                  </div>
                  <div style={{
                    height: '7px', borderRadius: '99px',
                    background: T.surface2, overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(100, (item.value / max) * 100)}%`,
                      background: item.color,
                      borderRadius: '99px',
                      transition: 'width 0.8s ease',
                    }} />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Summary totals at bottom */}
          <div style={{
            marginTop: '28px',
            paddingTop: '18px',
            borderTop: `1px solid ${T.border}`,
            display: 'flex', justifyContent: 'space-between',
          }}>
            {[
              { label: 'Per Meeting (avg)', value: data.total ? ((data.decisions + data.actions + data.topics) / data.total).toFixed(1) : '0' },
              { label: 'Total Insights',    value: data.decisions + data.actions + data.topics },
            ].map(s => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '20px', fontWeight: 800, color: T.text, letterSpacing: '-0.03em' }}>
                  {s.value}
                </div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: T.text3, marginTop: '3px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </Card>

      </div>
    </div>
  )
}