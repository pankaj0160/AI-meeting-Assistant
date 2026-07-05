// client/src/components/ProcessingCompleteReveal.jsx
//
// PHASE 2 (B3) — the one signature "wow" moment.
//
// WHY THIS EXISTS: previously, the progress bar hit 100% and the page
// just navigated away silently — the actual payoff (the AI found X
// decisions, Y action items...) only appeared after a full page
// transition to MeetingDetail. This is the core value prop of the whole
// product; it deserved a moment, not a silent redirect.
//
// Design intent (per the design guide's "one orchestrated moment per
// page load max" rule): ONE deliberate animation sequence — checkmark →
// summary teaser → counts landing one at a time — then either the user
// clicks through or it auto-advances. Nothing else on this screen
// animates competitively with it.

import { useEffect, useState } from 'react'
import { CheckCircle2, MessageSquare, CheckSquare, Tag, ArrowRight } from 'lucide-react'
import { useTheme } from '../ThemeContext'

function CountChip({ icon: Icon, label, value, color, bg, delay }) {
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setShown(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '10px 14px', borderRadius: '12px',
      background: bg, minWidth: '110px',
      opacity: shown ? 1 : 0,
      transform: shown ? 'translateY(0) scale(1)' : 'translateY(8px) scale(0.92)',
      transition: 'all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)',
    }}>
      <Icon size={16} color={color} />
      <div>
        <div style={{ fontSize: '17px', fontWeight: 800, color, lineHeight: 1, fontFamily: 'var(--font-mono, monospace)' }}>
          {value}
        </div>
        <div style={{ fontSize: '10px', color, opacity: 0.75, fontWeight: 600, marginTop: '2px' }}>
          {label}
        </div>
      </div>
    </div>
  )
}

/**
 * @param {string}   summary     one-line teaser of the meeting summary
 * @param {number}   decisions   count of decisions extracted
 * @param {number}   actions     count of action items extracted
 * @param {number}   topics      count of topics extracted
 * @param {function} onContinue  called when the user clicks through (or auto-advance fires)
 * @param {number}   autoAdvanceMs  ms before auto-navigating; 0 disables auto-advance
 */
export default function ProcessingCompleteReveal({
  summary, decisions = 0, actions = 0, topics = 0,
  onContinue, autoAdvanceMs = 3200,
}) {
  const { T } = useTheme()
  const [checkShown, setCheckShown] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setCheckShown(true), 60)
    if (autoAdvanceMs > 0) {
      const advance = setTimeout(onContinue, autoAdvanceMs)
      return () => { clearTimeout(t); clearTimeout(advance) }
    }
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const teaser = summary
    ? (summary.length > 130 ? summary.slice(0, 130).trim() + '…' : summary)
    : 'Your meeting has been fully processed.'

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(10px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 999,
    }}>
      <div className="anim-fade-up" style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: '24px', padding: '40px 36px',
        width: '100%', maxWidth: '440px', textAlign: 'center',
        boxShadow: T.cardShadow,
      }}>
        {/* Checkmark burst — the one animated centerpiece of this screen */}
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: T.accentBg, margin: '0 auto 20px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transform: checkShown ? 'scale(1)' : 'scale(0)',
          transition: 'transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}>
          <CheckCircle2 size={34} color={T.accent} strokeWidth={2} />
        </div>

        <h2 style={{
          fontSize: '20px', fontWeight: 800, color: T.text,
          letterSpacing: '-0.03em', margin: '0 0 10px',
        }}>
          Your meeting is ready
        </h2>

        <p style={{
          fontSize: '13.5px', color: T.text3, lineHeight: 1.6,
          margin: '0 0 24px', maxWidth: '360px', marginLeft: 'auto', marginRight: 'auto',
        }}>
          {teaser}
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '28px', flexWrap: 'wrap' }}>
          <CountChip icon={MessageSquare} label="decisions" value={decisions} color={T.amber}       bg={T.amberBg}   delay={250} />
          <CountChip icon={CheckSquare}   label="actions"   value={actions}   color={T.accent}      bg={T.accentBg}  delay={400} />
          <CountChip icon={Tag}           label="topics"    value={topics}    color="#22d3ee"        bg="rgba(6,182,212,0.12)" delay={550} />
        </div>

        <button
          onClick={onContinue}
          className="press"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '12px 26px', borderRadius: '11px', border: 'none',
            background: T.btnGrad, color: '#fff',
            fontSize: '14.5px', fontWeight: 700, cursor: 'pointer',
            fontFamily: 'inherit', boxShadow: T.btnShadow,
          }}
        >
          View full summary <ArrowRight size={15} />
        </button>
      </div>
    </div>
  )
}