// components/Toast.jsx
// Global toast notification system — success, error, info, warning
//
// HOW IT WORKS (three parts):
//
//   Part 1 — ToastContext: stores the list of active toasts globally.
//             Any component can call useToast() to add a toast.
//
//   Part 2 — ToastProvider: wraps the whole app (added to main.jsx).
//             Renders the floating toast container in the top-right corner.
//
//   Part 3 — useToast() hook: gives any component access to toast().
//             Usage: const { toast } = useToast()
//                    toast.success('Saved!', 'Your changes were saved.')
//                    toast.error('Failed', 'Could not connect to server.')
//
// WHY CONTEXT?
//   Toasts need to appear on top of everything regardless of which
//   component triggers them. Context lets any deeply-nested component
//   (e.g. a button inside a card inside a modal) show a toast without
//   passing callbacks down through props.

import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useTheme } from '../ThemeContext'

const ToastContext = createContext(null)

// ── Individual Toast ──────────────────────────────────────────────────────────
function ToastItem({ id, type, title, message, onRemove }) {
  const { T, isDark } = useTheme()
  const [leaving, setLeaving] = useState(false)

  // Auto-dismiss after 4 seconds
  useEffect(() => {
    const timer = setTimeout(() => dismiss(), 4000)
    return () => clearTimeout(timer)
  }, [])

  const dismiss = () => {
    setLeaving(true)
    // Wait for exit animation, then remove from state
    setTimeout(() => onRemove(id), 320)
  }

  const config = {
    success: {
      icon: '✓',
      iconBg: T.emerald,
      border: T.emerald,
      label: 'Success',
    },
    error: {
      icon: '✕',
      iconBg: T.danger,
      border: T.danger,
      label: 'Error',
    },
    warning: {
      icon: '!',
      iconBg: T.warning,
      border: T.warning,
      label: 'Warning',
    },
    info: {
      icon: 'i',
      iconBg: T.accent,
      border: T.accent,
      label: 'Info',
    },
  }[type] || {
    icon: 'i', iconBg: T.accent, border: T.accent, label: 'Info',
  }

  return (
    <div
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '12px',
        padding: '14px 16px',
        background: isDark ? 'rgba(13,17,32,0.96)' : 'rgba(255,255,255,0.96)',
        border: `1px solid ${config.border}44`,
        borderLeft: `3px solid ${config.border}`,
        borderRadius: 'var(--radius-md)',
        boxShadow: isDark
          ? '0 8px 32px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.04) inset'
          : '0 8px 32px rgba(0,0,0,0.12), 0 1px 0 rgba(255,255,255,0.8) inset',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        maxWidth: '360px',
        minWidth: '260px',
        animation: `${leaving ? 'toastOut' : 'toastIn'} 0.32s cubic-bezier(0.4,0,0.2,1) both`,
        cursor: 'pointer',
        userSelect: 'none',
      }}
      onClick={dismiss}
    >
      {/* Icon circle */}
      <div style={{
        width: '26px', height: '26px',
        borderRadius: '50%',
        background: `${config.iconBg}22`,
        border: `1px solid ${config.iconBg}44`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        fontSize: '12px', fontWeight: 800,
        color: config.iconBg,
      }}>
        {config.icon}
      </div>

      {/* Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '13.5px', fontWeight: 600,
          color: isDark ? '#f0f4ff' : '#0f0e0a',
          marginBottom: message ? '2px' : 0,
        }}>
          {title}
        </div>
        {message && (
          <div style={{
            fontSize: '12px',
            color: isDark ? 'rgba(180,190,220,0.75)' : '#6b6556',
            lineHeight: 1.5,
          }}>
            {message}
          </div>
        )}
      </div>

      {/* Close hint */}
      <div style={{
        fontSize: '16px', lineHeight: 1,
        color: isDark ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.22)',
        flexShrink: 0, marginTop: '1px',
      }}>
        ×
      </div>
    </div>
  )
}

// ── Provider ──────────────────────────────────────────────────────────────────
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const add = useCallback((type, title, message) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    setToasts(prev => [...prev, { id, type, title, message }])
  }, [])

  const remove = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // Expose four shorthand methods: toast.success(), toast.error() etc.
  const toast = {
    success: (title, message) => add('success', title, message),
    error:   (title, message) => add('error',   title, message),
    warning: (title, message) => add('warning', title, message),
    info:    (title, message) => add('info',    title, message),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Floating container — fixed top-right, above everything */}
      <div style={{
        position: 'fixed',
        top: '20px', right: '20px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        pointerEvents: toasts.length ? 'auto' : 'none',
      }}>
        {toasts.map(t => (
          <ToastItem key={t.id} {...t} onRemove={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}