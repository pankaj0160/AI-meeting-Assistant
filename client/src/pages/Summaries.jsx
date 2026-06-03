// client/src/pages/Summaries.jsx

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, ArrowRight } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { getMeetings, getMeetingIntelligence } from '../api/client'
import { PageHeader, Card, EmptyState, Skeleton } from '../components/ui'

export default function Summaries() {
  const { T } = useTheme()
  const navigate = useNavigate()
  const [summaries, setSummaries] = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const meetings = await getMeetings()
        const results = []
        await Promise.all(
          meetings.slice(0, 20).map(async m => {
            try {
              const intel = await getMeetingIntelligence(m.id)
              if (intel?.summary) {
                results.push({
                  id: m.id,
                  filename: m.filename,
                  created_at: m.created_at,
                  summary: intel.summary,
                  topics: intel.topics || [],
                })
              }
            } catch {}
          })
        )
        results.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        setSummaries(results)
      } catch {}
      finally { setLoading(false) }
    }
    load()
  }, [])

  function fmt(iso) {
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      })
    } catch { return '—' }
  }

  return (
    <div>
      <PageHeader
        title="Summaries"
        subtitle={`${summaries.length} meeting summaries`}
      />

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[1,2,3].map(i => (
            <Card key={i}>
              <Skeleton width="40%" height="18px" style={{ marginBottom: '12px' }} />
              <Skeleton width="100%" height="14px" style={{ marginBottom: '8px' }} />
              <Skeleton width="85%" height="14px" style={{ marginBottom: '8px' }} />
              <Skeleton width="60%" height="14px" />
            </Card>
          ))}
        </div>
      ) : summaries.length === 0 ? (
        <EmptyState
          icon="📋"
          title="No summaries yet"
          subtitle="Process a meeting to generate AI summaries."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {summaries.map((s, i) => (
            <div
              key={s.id}
              className="anim-fade-up"
              style={{ animationDelay: `${i * 0.06}s` }}
            >
              <Card
                hoverable
                onClick={() => navigate(`/app/meetings/${s.id}`)}
              >
                <div style={{
                  display: 'flex', alignItems: 'flex-start',
                  justifyContent: 'space-between', gap: '16px',
                  marginBottom: '14px',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{
                      width: '36px', height: '36px', borderRadius: '9px',
                      background: T.blueBg, flexShrink: 0,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <FileText size={17} color={T.blueText} />
                    </div>
                    <div>
                      <div style={{
                        fontSize: '16px', fontWeight: 700,
                        color: T.text, letterSpacing: '-0.02em',
                      }}>
                        {s.filename || 'Untitled Meeting'}
                      </div>
                      <div style={{ fontSize: '12px', color: T.text3, marginTop: '2px' }}>
                        {fmt(s.created_at)}
                      </div>
                    </div>
                  </div>
                  <ArrowRight size={16} color={T.text4} style={{ flexShrink: 0, marginTop: '4px' }} />
                </div>

                <p style={{
                  fontSize: '15px', fontWeight: 400,
                  color: T.text2, lineHeight: 1.75,
                  margin: '0 0 16px',
                }}>
                  {s.summary}
                </p>

                {s.topics.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {s.topics.map((t, j) => (
                      <span key={j} style={{
                        padding: '3px 10px', borderRadius: '99px',
                        fontSize: '12px', fontWeight: 600,
                        color: T.cyanText, background: T.cyanBg,
                      }}>
                        {t.title}
                      </span>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}