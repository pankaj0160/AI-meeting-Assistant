// client/src/components/OnboardingChecklist.jsx
//
// PHASE 2 (B1) — onboarding flow.
//
// WHY THIS EXISTS: a brand new user's Dashboard was just a stat row of
// zeros and an empty meetings list. Nothing walked them through what to
// do first. This card replaces that with an explicit 3-step flow and
// disappears once it's done its job — it's not meant to live forever.
//
// Driven entirely by REAL data (meeting count, whether anything has been
// extracted yet) rather than fake client-only progress — so it can't get
// out of sync with what actually happened.

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Sparkles, LayoutDashboard, Check, X, ArrowRight } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { Card } from './ui'

function dismissKey(userId) {
  return `summly-onboarding-dismissed-${userId || 'anon'}`
}

/**
 * @param {number} meetingsCount   total meetings the user has (from stats)
 * @param {number} insightsCount   total decisions+actions+topics extracted
 *                                  so far — used to detect "the AI actually
 *                                  found something," not just "a file exists"
 * @param {number} userId          for a per-user dismissal flag in localStorage
 */
export default function OnboardingChecklist({ meetingsCount = 0, insightsCount = 0, userId }) {
  const { T, isDark } = useTheme()
  const navigate = useNavigate()
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(dismissKey(userId)) === '1')
    } catch {
      // localStorage unavailable (private browsing, etc.) — just show it.
    }
  }, [userId])

  const handleDismiss = () => {
    setDismissed(true)
    try { localStorage.setItem(dismissKey(userId), '1') } catch {}
  }

  const step1Done = meetingsCount > 0
  const step2Done = insightsCount > 0
  const step3Done = step2Done // "explore your dashboard" — unlocked once there's something to explore

  // Graduate automatically once the user has a couple of processed
  // meetings — at that point this card has done its job and a persistent
  // "getting started" banner would just be clutter, not guidance.
  const graduated = meetingsCount >= 2 && insightsCount > 0

  if (dismissed || graduated) return null

  const steps = [
    {
      icon: Upload,
      title: 'Upload your first meeting',
      subtitle: 'A recording, or paste a YouTube link — either works.',
      done: step1Done,
      cta: !step1Done && { label: 'Upload now', onClick: () => navigate('/app/upload') },
    },
    {
      icon: Sparkles,
      title: 'Let Summly extract the insights',
      subtitle: 'Summary, decisions, and action items — pulled out automatically.',
      done: step2Done,
      cta: step1Done && !step2Done && { label: 'View progress', onClick: () => navigate('/app/meetings') },
    },
    {
      icon: LayoutDashboard,
      title: 'Explore what it found',
      subtitle: 'Check Analytics for trends, or Tasks for everything assigned to your team.',
      done: step3Done,
      cta: step3Done && { label: 'See Analytics', onClick: () => navigate('/app/analytics') },
    },
  ]

  const doneCount = steps.filter(s => s.done).length

  return (
    <Card style={{ padding: '24px', marginBottom: '20px', position: 'relative', overflow: 'hidden' }}>
      {/* Dismiss button — always available, never force anyone through this */}
      <button
        onClick={handleDismiss}
        aria-label="Dismiss getting started guide"
        style={{
          position: 'absolute', top: '16px', right: '16px',
          width: '28px', height: '28px', borderRadius: '8px',
          border: 'none', background: 'transparent', color: T.text3,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', transition: 'all 0.15s ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = T.surface2; e.currentTarget.style.color = T.text }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = T.text3 }}
      >
        <X size={15} />
      </button>

      <div style={{ marginBottom: '18px', paddingRight: '32px' }}>
        <div style={{ fontSize: '15px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
          Getting started
        </div>
        <div style={{ fontSize: '12px', color: T.text3, marginTop: '3px' }}>
          {doneCount} of {steps.length} steps done — takes about 5 minutes total.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
        {steps.map((s, i) => {
          const Icon = s.icon
          return (
            <div
              key={s.title}
              style={{
                padding: '16px', borderRadius: '14px',
                border: `1px solid ${s.done ? T.accent + '33' : T.border}`,
                background: s.done ? T.accentBg : T.surface2,
                opacity: s.done ? 0.85 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <div style={{
                  width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                  background: s.done ? T.accent : T.surface,
                  border: s.done ? 'none' : `1px solid ${T.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {s.done ? <Check size={13} color="#fff" strokeWidth={3} /> : <Icon size={13} color={T.text3} />}
                </div>
                <div style={{ fontSize: '13.5px', fontWeight: 700, color: T.text }}>
                  {i + 1}. {s.title}
                </div>
              </div>
              <div style={{ fontSize: '12px', color: T.text3, lineHeight: 1.5, marginBottom: s.cta ? '10px' : 0 }}>
                {s.subtitle}
              </div>
              {s.cta && (
                <button
                  onClick={s.cta.onClick}
                  className="press"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', fontWeight: 700, color: T.accent,
                    background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  {s.cta.label} <ArrowRight size={12} />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}