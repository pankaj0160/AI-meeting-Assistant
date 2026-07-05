// client/src/components/CommitmentReliability.jsx
//
// PHASE 2 — headline differentiator feature.
//
// Shows, per person, whether they follow through on what they commit to
// in meetings — not just "task done eventually" but "done ON TIME."
// This is the stat nobody else in this space surfaces: aggregated across
// every meeting a person has been assigned an action item in.
//
// Reusable: used on the Analytics page (full context) and can be dropped
// onto the Dashboard as a compact widget (see `compact` prop) since it's
// exactly the kind of "wow, it knows that?" detail worth surfacing early.

import { useTheme } from '../ThemeContext'
import { Card, EmptyState } from './ui'

function reliabilityColor(pct, T) {
  if (pct === null || pct === undefined) return T.text3
  if (pct >= 80) return T.accent
  if (pct >= 50) return T.amber
  return T.danger
}

function reliabilityBg(pct, T) {
  if (pct === null || pct === undefined) return T.border
  if (pct >= 80) return T.accentBg
  if (pct >= 50) return T.amberBg
  return T.dangerBg
}

function PersonRow({ person, T, compact }) {
  const { owner, reliability_pct, has_enough_data, done_on_time, done_late, missed, resolved_count } = person
  const color = reliabilityColor(reliability_pct, T)
  const bg    = reliabilityBg(reliability_pct, T)

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '14px',
      padding: compact ? '10px 0' : '14px 0',
      borderBottom: `1px solid ${T.border}`,
    }}>
      {/* Avatar initial */}
      <div style={{
        width: compact ? 28 : 34, height: compact ? 28 : 34, borderRadius: '50%',
        background: bg, color, fontWeight: 700,
        fontSize: compact ? '12px' : '13px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, textTransform: 'uppercase',
      }}>
        {owner?.[0] || '?'}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: compact ? '13px' : '14px', fontWeight: 600, color: T.text,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {owner}
        </div>
        {!compact && (
          has_enough_data ? (
            <div style={{ fontSize: '11px', color: T.text3, marginTop: '2px' }}>
              {done_on_time} on time · {done_late} late · {missed} missed
            </div>
          ) : (
            <div style={{ fontSize: '11px', color: T.text3, marginTop: '2px' }}>
              Not enough data yet ({resolved_count}/3 resolved)
            </div>
          )
        )}
      </div>

      {/* Reliability bar + percentage */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        {has_enough_data ? (
          <>
            <div style={{
              width: compact ? 50 : 70, height: 6, borderRadius: 3,
              background: T.border, overflow: 'hidden',
            }}>
              <div style={{
                width: `${reliability_pct}%`, height: '100%',
                background: color, borderRadius: 3,
                transition: 'width 0.4s ease',
              }} />
            </div>
            <div style={{
              fontSize: compact ? '13px' : '15px', fontWeight: 800, color,
              minWidth: compact ? '32px' : '40px', textAlign: 'right',
              fontFamily: 'var(--font-mono, monospace)',
            }}>
              {reliability_pct}%
            </div>
          </>
        ) : (
          <span style={{ fontSize: '11px', color: T.text3, fontStyle: 'italic' }}>—</span>
        )}
      </div>
    </div>
  )
}

/**
 * @param {object[]} people - array from GET /commitments/reliability (`.people`)
 *                             or the `commitment_reliability` field of GET /analytics
 * @param {boolean}  compact - tighter rows, no breakdown line, for dashboard widgets
 * @param {number}   limit   - max rows to show (e.g. top 5 on a dashboard widget)
 */
export default function CommitmentReliability({ people, compact = false, limit }) {
  const { T } = useTheme()
  const rows = limit ? (people || []).slice(0, limit) : (people || [])

  if (!rows.length) {
    return (
      <EmptyState
        icon="🤝"
        title="No commitments tracked yet"
        subtitle="Once meetings have action items with named owners, you'll see who follows through here."
      />
    )
  }

  return (
    <div>
      {rows.map((p) => (
        <PersonRow key={p.owner} person={p} T={T} compact={compact} />
      ))}
    </div>
  )
}