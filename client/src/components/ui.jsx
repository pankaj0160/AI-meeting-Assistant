// components/ui.jsx
// Phase 3 upgrade — premium components used across all pages

import { useTheme } from '../ThemeContext'
import { useEffect, useRef, useState } from 'react'

// ── Page Header ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, action, eyebrow }) {
  const { T } = useTheme()
  return (
    <div
      className="anim-fade-up"
      style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
        marginBottom: '36px',
      }}
    >
      <div>
        {eyebrow && (
          <div style={{
            fontSize: '11px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: T.accent, marginBottom: '6px',
          }}>
            {eyebrow}
          </div>
        )}
        <h1 style={{
          fontSize: '32px', fontWeight: 800,
          letterSpacing: '-0.05em', lineHeight: 1.1,
          color: T.text, margin: 0,
          fontFamily: 'var(--font-display, var(--font))',
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            fontSize: '15px', fontWeight: 400,
            color: T.text3, margin: '8px 0 0',
            lineHeight: 1.6,
          }}>
            {subtitle}
          </p>
        )}
      </div>
      {action && (
        <div className="anim-fade-in" style={{ animationDelay: '0.1s' }}>
          {action}
        </div>
      )}
    </div>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────
// Standard surface card with optional hover lift
export function Card({ children, style = {}, hoverable = false, onClick }) {
  const { T } = useTheme()
  // A div with onClick and nothing else is invisible to keyboard/screen-reader
  // users — no tab stop, no way to activate it, no announced role. Card is
  // used as a clickable surface throughout the app (meeting cards, stat
  // cards), so this fix has app-wide reach.
  const a11yProps = onClick ? {
    role: 'button',
    tabIndex: 0,
    onKeyDown: (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e) }
    },
  } : {}
  return (
    <div
      onClick={onClick}
      className={onClick ? 'press' : ''}
      {...a11yProps}
      style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 'var(--radius-lg)',
        boxShadow: T.cardShadow,
        padding: '28px',
        transition: 'box-shadow var(--speed) var(--ease), transform var(--speed) var(--ease), border-color var(--speed) var(--ease)',
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
      onMouseEnter={e => {
        if (hoverable || onClick) {
          // No shadow-grow on hover — the guide calls this out specifically
          // as the most overused, templated micro-interaction in AI-generated
          // UI. Border + a 1px lift reads as considered; a bigger shadow
          // reads as a default someone left in.
          e.currentTarget.style.borderColor = T.border2
          e.currentTarget.style.transform = 'translateY(-1px)'
        }
      }}
      onMouseLeave={e => {
        if (hoverable || onClick) {
          e.currentTarget.style.borderColor = T.border
          e.currentTarget.style.transform = 'translateY(0)'
        }
      }}
    >
      {children}
    </div>
  )
}

// ── Glass Card ────────────────────────────────────────────────────────────────
// Premium frosted-glass card — use for hero sections and highlight areas
// backdrop-filter blurs what is BEHIND the element, creating depth layering
export function GlassCard({ children, style = {}, onClick }) {
  const { T, isDark } = useTheme()
  const a11yProps = onClick ? {
    role: 'button',
    tabIndex: 0,
    onKeyDown: (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e) }
    },
  } : {}
  return (
    <div
      onClick={onClick}
      className="glass press"
      {...a11yProps}
      style={{
        background: isDark
          ? 'rgba(13,17,32,0.72)'
          : 'rgba(255,255,255,0.72)',
        border: `1px solid ${isDark ? 'rgba(16,185,129,0.16)' : 'rgba(5,150,105,0.14)'}`,
        borderRadius: 'var(--radius-xl)',
        boxShadow: isDark
          ? '0 8px 40px rgba(0,0,0,0.45), 0 1px 0 rgba(255,255,255,0.04) inset'
          : '0 8px 32px rgba(5,150,105,0.08), 0 1px 0 rgba(255,255,255,0.8) inset',
        padding: '28px',
        transition: 'box-shadow var(--speed) var(--ease), transform var(--speed) var(--ease)',
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
      onMouseEnter={e => {
        if (onClick) {
          e.currentTarget.style.transform = 'translateY(-2px)'
          e.currentTarget.style.boxShadow = isDark
            ? '0 12px 48px rgba(0,0,0,0.55), 0 0 0 1px rgba(16,185,129,0.22)'
            : '0 12px 40px rgba(5,150,105,0.16), 0 0 0 1px rgba(5,150,105,0.18)'
        }
      }}
      onMouseLeave={e => {
        if (onClick) {
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = isDark
            ? '0 8px 40px rgba(0,0,0,0.45), 0 1px 0 rgba(255,255,255,0.04) inset'
            : '0 8px 32px rgba(5,150,105,0.08), 0 1px 0 rgba(255,255,255,0.8) inset'
        }
      }}
    >
      {children}
    </div>
  )
}

// ── Animated Stat Card ────────────────────────────────────────────────────────
// Numbers count up from 0 when the card first mounts.
// This is achieved with requestAnimationFrame — smoother than setInterval.
// requestAnimationFrame fires before the browser paints each frame (~60fps).
export function StatCard({ label, value, icon, color, bg, delay = 0, trend }) {
  const { T } = useTheme()
  const [display, setDisplay] = useState(0)
  const frameRef = useRef(null)

  // Count-up animation
  // How it works:
  //   1. We know the target value and the duration (1000ms)
  //   2. Each frame: calculate how far along we are (progress 0→1)
  //   3. Multiply target by progress to get current display value
  //   4. When progress reaches 1 — stop and show exact final value
  useEffect(() => {
    if (typeof value !== 'number') { setDisplay(value); return }
    const duration  = 900
    const startTime = performance.now()
    const startVal  = 0

    const tick = (now) => {
      const elapsed  = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // easeOutExpo: fast start, slow finish — feels satisfying
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      setDisplay(Math.round(startVal + (value - startVal) * eased))
      if (progress < 1) frameRef.current = requestAnimationFrame(tick)
    }

    // Delay before starting (for stagger effect)
    const timer = setTimeout(() => {
      frameRef.current = requestAnimationFrame(tick)
    }, delay * 1000)

    return () => {
      clearTimeout(timer)
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
  }, [value, delay])

  return (
    <div className="anim-fade-up" style={{ animationDelay: `${delay}s` }}>
      <Card>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              fontSize: '11px', fontWeight: 700,
              letterSpacing: '0.10em', textTransform: 'uppercase',
              color: T.text3, marginBottom: '10px',
            }}>
              {label}
            </div>
            {/* Number with count-up — Fraunces display face, per typography pass:
                dashboard stat numbers are the "big number" moment where the
                display face should show up, not just page titles. */}
            <div style={{
              fontFamily: 'var(--font-display, var(--font))',
              fontSize: '38px', fontWeight: 600,
              letterSpacing: '-0.02em', lineHeight: 1,
              color: T.text,
              fontVariantNumeric: 'tabular-nums',
            }}>
              {typeof value === 'number' ? display : value}
            </div>
            {/* Optional trend indicator */}
            {trend && (
              <div style={{
                marginTop: '8px',
                fontSize: '12px', fontWeight: 500,
                color: trend > 0 ? T.emerald : T.danger,
                display: 'flex', alignItems: 'center', gap: '3px',
              }}>
                {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last week
              </div>
            )}
          </div>
          {/* Icon box with glow */}
          <div style={{
            width: '48px', height: '48px',
            borderRadius: '14px',
            background: bg,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '22px',
            flexShrink: 0,
            boxShadow: `0 4px 16px ${color}30`,
          }}>
            {icon}
          </div>
        </div>
      </Card>
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
// Horizontal tab bar. Controlled component — parent manages activeTab state.
// Usage:
//   const [tab, setTab] = useState('summary')
//   <Tabs tabs={[{ id: 'summary', label: 'Summary', icon: '📝' }]}
//         active={tab} onChange={setTab} />
export function Tabs({ tabs, active, onChange }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', gap: '4px',
      padding: '4px',
      background: T.surface2,
      borderRadius: 'var(--radius-md)',
      border: `1px solid ${T.border}`,
      width: 'fit-content',
      marginBottom: '24px',
    }}>
      {tabs.map(tab => {
        const isActive = tab.id === active
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '7px 16px',
              borderRadius: 'calc(var(--radius-md) - 2px)',
              border: isActive ? `1px solid ${T.border2}` : '1px solid transparent',
              background: isActive ? T.surface : 'transparent',
              color: isActive ? T.text : T.text3,
              fontSize: '13px', fontWeight: isActive ? 600 : 500,
              cursor: 'pointer',
              transition: 'all var(--speed-fast) var(--ease)',
              boxShadow: isActive ? T.cardShadow : 'none',
              fontFamily: 'inherit',
              whiteSpace: 'nowrap',
            }}
          >
            {tab.icon && <span style={{ fontSize: '14px' }}>{tab.icon}</span>}
            {tab.label}
            {tab.count !== undefined && (
              <span style={{
                fontSize: '10px', fontWeight: 700,
                padding: '1px 6px', borderRadius: '99px',
                background: isActive ? T.accentBg : T.surface3,
                color: isActive ? T.accent : T.text3,
              }}>
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

// ── Section Label ─────────────────────────────────────────────────────────────
export function SectionLabel({ children, action }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '14px',
    }}>
      <div style={{
        fontSize: '11px', fontWeight: 700,
        letterSpacing: '0.10em', textTransform: 'uppercase',
        color: T.text3,
      }}>
        {children}
      </div>
      {action && action}
    </div>
  )
}

// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ children, color, bg, dot = false }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '5px',
      padding: '3px 10px',
      borderRadius: '99px',
      // Mono face for badges/tags — ties short-label UI chrome back to
      // the product's actual material (timestamped, structured meeting data)
      // instead of reading as generic pill-shaped UI decoration.
      fontFamily: 'var(--font-mono, var(--font))',
      fontSize: '11px', fontWeight: 500,
      letterSpacing: '0.02em',
      color, background: bg,
    }}>
      {dot && (
        <span style={{
          width: '5px', height: '5px', borderRadius: '50%',
          background: color, flexShrink: 0,
        }} />
      )}
      {children}
    </span>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────
export function Button({
  children, onClick, variant = 'primary',
  size = 'md', disabled = false, loading = false,
  icon, style: extraStyle = {}, type = 'button',
}) {
  const { T } = useTheme()

  const sizes = {
    sm: { padding: '7px 14px',  fontSize: '12.5px', borderRadius: 'var(--radius-md)', gap: '6px' },
    md: { padding: '10px 20px', fontSize: '14px',   borderRadius: 'var(--radius-md)', gap: '7px' },
    lg: { padding: '13px 28px', fontSize: '15px',   borderRadius: 'var(--radius-lg)', gap: '8px' },
  }

  const variants = {
    primary: {
      background: T.btnGrad,
      color: '#fff',
      border: 'none',
      boxShadow: T.btnShadow,
    },
    secondary: {
      background: T.surface2,
      color: T.text2,
      border: `1px solid ${T.border}`,
      boxShadow: 'none',
    },
    ghost: {
      background: 'transparent',
      color: T.text3,
      border: `1px solid ${T.border}`,
      boxShadow: 'none',
    },
    danger: {
      background: T.dangerBg,
      color: T.danger,
      border: `1px solid ${T.danger}44`,
      boxShadow: 'none',
    },
    accent: {
      background: T.accentBg,
      color: T.accent,
      border: `1px solid ${T.accent}44`,
      boxShadow: 'none',
    },
  }

  const s = sizes[size]

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className="press"
      style={{
        display: 'inline-flex', alignItems: 'center',
        justifyContent: 'center', gap: s.gap,
        borderRadius: s.borderRadius,
        padding: s.padding, fontSize: s.fontSize,
        fontWeight: 600,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all var(--speed) var(--ease)',
        outline: 'none',
        ...variants[variant],
        ...extraStyle,
      }}
      onMouseEnter={e => {
        if (!disabled && !loading) {
          e.currentTarget.style.opacity = '0.88'
          e.currentTarget.style.transform = 'translateY(-1px)'
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.opacity = '1'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      {loading
        // Waveform-bar spinner instead of a generic circular one — this
        // .waveform-spinner CSS already existed in index.css but was never
        // actually used anywhere. Free brand moment: every loading button
        // now pulses with the same motif as the product's core material.
        ? (
          <span className="waveform-spinner" aria-hidden="true">
            <span /><span /><span />
          </span>
        )
        : icon
      }
      {children}
    </button>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────
// A flat-lined waveform sits behind the context icon on every empty state —
// this is the "reuse brand material instead of a generic illustration" idea
// from the guide. It's decorative-only (aria-hidden) and low-opacity so it
// doesn't compete with the icon/copy, which stay page-specific and already
// use in-product-voice copy (checked across all 13 call sites — genuinely
// nothing generic like "No data" anywhere already).
function EmptyStateWaveform({ T }) {
  // 9 bars, flat/low amplitude — deliberately calmer than the loading
  // spinner's pulse, since this represents "nothing here yet" rather than
  // "something is happening."
  const heights = [4, 7, 5, 10, 6, 11, 5, 8, 4]
  return (
    <svg width="140" height="24" viewBox="0 0 140 24" fill="none" aria-hidden="true"
      style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
      {heights.map((h, i) => (
        <rect key={i} x={i * 15 + 2} y={12 - h / 2} width="6" height={h} rx="3" fill={T.text4} />
      ))}
    </svg>
  )
}

export function EmptyState({ icon, title, subtitle, action }) {
  const { T } = useTheme()
  return (
    <div
      className="anim-scale-in"
      style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '72px 32px', textAlign: 'center',
      }}
    >
      <div style={{
        position: 'relative',
        width: '140px', height: '52px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '20px',
      }}>
        <EmptyStateWaveform T={T} />
        <div style={{
          position: 'relative',
          fontSize: '52px', lineHeight: 1,
          opacity: 0.45, filter: 'grayscale(20%)',
        }}>
          {icon}
        </div>
      </div>
      <div style={{
        fontSize: '19px', fontWeight: 700,
        letterSpacing: '-0.03em',
        color: T.text, marginBottom: '8px',
      }}>
        {title}
      </div>
      <div style={{
        fontSize: '14px', color: T.text3,
        lineHeight: 1.65, maxWidth: '320px',
        marginBottom: action ? '28px' : 0,
      }}>
        {subtitle}
      </div>
      {action && action}
    </div>
  )
}

// ── Skeleton Block ────────────────────────────────────────────────────────────
export function Skeleton({ width = '100%', height = '20px', style = {} }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: 'var(--radius-md)', ...style }}
    />
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider({ label }) {
  const { T } = useTheme()
  if (label) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        margin: '20px 0',
      }}>
        <div style={{ flex: 1, height: '1px', background: T.border }} />
        <span style={{ fontSize: '11px', color: T.text3, fontWeight: 500 }}>{label}</span>
        <div style={{ flex: 1, height: '1px', background: T.border }} />
      </div>
    )
  }
  return <div style={{ height: '1px', background: T.border, margin: '24px 0' }} />
}

// ── Tag ───────────────────────────────────────────────────────────────────────
export function Tag({ children, color, bg }) {
  const { T } = useTheme()
  return (
    <span style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '99px',
      fontFamily: 'var(--font-mono, var(--font))',
      fontSize: '11.5px', fontWeight: 500,
      color: color || T.accentLight,
      background: bg || T.accentBg,
      border: `1px solid ${color || T.accent}22`,
      letterSpacing: '0.02em',
    }}>
      {children}
    </span>
  )
}

// ── Score Ring ────────────────────────────────────────────────────────────────
// Animated SVG circle that fills from 0 to `score` on mount.
// Used on Meeting Detail health score.
//
// How SVG stroke-dashoffset works:
//   stroke-dasharray  = the total length of dashes (we set it = circumference)
//   stroke-dashoffset = how far to push the dash pattern backwards
//   offset=circumference = nothing visible (all pushed out of view)
//   offset=0             = full circle visible
//   So animating offset from circumference → target_offset draws the arc.
export function ScoreRing({ score = 0, size = 120, strokeWidth = 10, color, label }) {
  const { T } = useTheme()
  const [animated, setAnimated] = useState(0)
  const radius        = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const targetOffset  = circumference - (animated / 100) * circumference

  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimated(score)
    }, 300)
    return () => clearTimeout(timer)
  }, [score])

  const ringColor = color || (
    score >= 80 ? T.emerald :
    score >= 60 ? T.warning :
    T.danger
  )

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background track */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={T.border}
          strokeWidth={strokeWidth}
        />
        {/* Animated fill arc */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={ringColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={targetOffset}
          style={{
            transition: 'stroke-dashoffset 1.2s cubic-bezier(0, 0, 0.2, 1)',
            filter: `drop-shadow(0 0 6px ${ringColor}80)`,
          }}
        />
      </svg>
      {/* Center content */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          fontSize: size > 100 ? '26px' : '18px',
          fontWeight: 800, letterSpacing: '-0.04em',
          color: ringColor,
          fontVariantNumeric: 'tabular-nums',
        }}>
          {animated}
        </div>
        {label && (
          <div style={{ fontSize: '10px', color: T.text3, fontWeight: 600, marginTop: '1px' }}>
            {label}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Kbd ───────────────────────────────────────────────────────────────────────
// Keyboard shortcut display. Usage: <Kbd>⌘K</Kbd>
export function Kbd({ children }) {
  const { T } = useTheme()
  return (
    <kbd style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      padding: '2px 7px',
      borderRadius: '5px',
      fontSize: '11px', fontWeight: 600,
      fontFamily: 'var(--font-mono, monospace)',
      color: T.text3,
      background: T.surface2,
      border: `1px solid ${T.border2}`,
      boxShadow: `0 1px 0 ${T.border2}`,
      lineHeight: 1.5,
    }}>
      {children}
    </kbd>
  )
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value = 0, max = 100, color, height = 6 }) {
  const { T } = useTheme()
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const barColor = color || T.accent

  return (
    <div style={{
      width: '100%', height,
      background: T.border,
      borderRadius: '99px',
      overflow: 'hidden',
    }}>
      <div style={{
        height: '100%',
        width: `${pct}%`,
        background: barColor,
        borderRadius: '99px',
        boxShadow: `0 0 8px ${barColor}60`,
        transition: 'width 0.8s cubic-bezier(0, 0, 0.2, 1)',
      }} />
    </div>
  )
}