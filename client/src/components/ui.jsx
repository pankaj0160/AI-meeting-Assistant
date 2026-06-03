// client/src/components/ui.jsx

import { useTheme } from '../ThemeContext'

// ── Page Header ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, action }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start',
      justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
      marginBottom: '36px',
    }}>
      <div>
        <h1 style={{
          fontSize: '34px', fontWeight: 800,
          letterSpacing: '-0.05em', lineHeight: 1.1,
          color: T.text, margin: 0,
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{
            fontSize: '16px', fontWeight: 400,
            color: T.text3, margin: '8px 0 0',
            lineHeight: 1.5,
          }}>
            {subtitle}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, style = {}, hoverable = false, onClick }) {
  const { T } = useTheme()
  return (
    <div
      onClick={onClick}
      style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 'var(--radius-lg)',
        boxShadow: T.cardShadow,
        padding: '28px',
        transition: 'box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease',
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
      onMouseEnter={e => {
        if (hoverable || onClick) {
          e.currentTarget.style.boxShadow = T.cardShadowHover
          e.currentTarget.style.borderColor = T.border2
          e.currentTarget.style.transform = 'translateY(-1px)'
        }
      }}
      onMouseLeave={e => {
        if (hoverable || onClick) {
          e.currentTarget.style.boxShadow = T.cardShadow
          e.currentTarget.style.borderColor = T.border
          e.currentTarget.style.transform = 'translateY(0)'
        }
      }}
    >
      {children}
    </div>
  )
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
export function StatCard({ label, value, icon, color, bg, delay = 0 }) {
  const { T } = useTheme()
  return (
    <div
      className={`anim-fade-up`}
      style={{ animationDelay: `${delay}s` }}
    >
      <Card>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{
              fontSize: '12px', fontWeight: 700,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: T.text3, marginBottom: '12px',
            }}>
              {label}
            </div>
            <div style={{
              fontSize: '36px', fontWeight: 800,
              letterSpacing: '-0.04em', lineHeight: 1,
              color: T.text,
            }}>
              {value}
            </div>
          </div>
          <div style={{
            width: '44px', height: '44px',
            borderRadius: '12px',
            background: bg,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '20px',
            flexShrink: 0,
          }}>
            {icon}
          </div>
        </div>
      </Card>
    </div>
  )
}

// ── Section Label ─────────────────────────────────────────────────────────────
export function SectionLabel({ children }) {
  const { T } = useTheme()
  return (
    <div style={{
      fontSize: '11px', fontWeight: 700,
      letterSpacing: '0.10em', textTransform: 'uppercase',
      color: T.text3, marginBottom: '14px',
    }}>
      {children}
    </div>
  )
}

// ── Badge ─────────────────────────────────────────────────────────────────────
export function Badge({ children, color, bg }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '3px 10px',
      borderRadius: '99px',
      fontSize: '12px', fontWeight: 600,
      letterSpacing: '0.02em',
      color, background: bg,
    }}>
      {children}
    </span>
  )
}

// ── Button ────────────────────────────────────────────────────────────────────
export function Button({
  children, onClick, variant = 'primary',
  size = 'md', disabled = false, loading = false,
  icon, style: extraStyle = {}
}) {
  const { T } = useTheme()

  const sizes = {
    sm: { padding: '7px 14px', fontSize: '13px' },
    md: { padding: '10px 20px', fontSize: '14px' },
    lg: { padding: '13px 28px', fontSize: '15px' },
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
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: 'inline-flex', alignItems: 'center',
        justifyContent: 'center', gap: '8px',
        borderRadius: 'var(--radius-md)',
        fontWeight: 600,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all 0.15s ease',
        outline: 'none',
        ...sizes[size],
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
        ? <span className="spinner" style={{ width: 14, height: 14 }} />
        : icon
      }
      {children}
    </button>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, subtitle, action }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '72px 32px', textAlign: 'center',
    }}>
      <div style={{
        fontSize: '48px', marginBottom: '20px',
        opacity: 0.5,
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: '20px', fontWeight: 700,
        letterSpacing: '-0.03em',
        color: T.text, marginBottom: '10px',
      }}>
        {title}
      </div>
      <div style={{
        fontSize: '15px', color: T.text3,
        lineHeight: 1.6, maxWidth: '340px',
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
      style={{ width, height, ...style }}
    />
  )
}

// ── Divider ───────────────────────────────────────────────────────────────────
export function Divider() {
  const { T } = useTheme()
  return (
    <div style={{
      height: '1px',
      background: T.border,
      margin: '24px 0',
    }} />
  )
}

// ── Tag ───────────────────────────────────────────────────────────────────────
export function Tag({ children, color, bg }) {
  const { T } = useTheme()
  return (
    <span style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '99px',
      fontSize: '12px', fontWeight: 600,
      color: color || T.accentLight,
      background: bg || T.accentBg,
      letterSpacing: '0.02em',
    }}>
      {children}
    </span>
  )
}