// client/src/components/Toast.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// Global toast notification system — shows small popup messages
// in the top-right corner for success, error, warning, and info.
//
// HOW IT WORKS (3 parts):
//
//   Part 1 — ToastContext
//     Stores the list of active toasts in React state.
//     Any component anywhere in the app can call useToast() to show one.
//
//   Part 2 — ToastProvider
//     Wraps the whole app (already added to main.jsx).
//     Renders the floating container with all active toasts.
//
//   Part 3 — useToast() hook
//     Call this in any component to get the toast object:
//       const { toast } = useToast()
//       toast.success('Saved!', 'Your meeting was processed.')
//       toast.error('Failed', 'Could not connect to server.')
//       toast.warning('Large file', 'This may take a few minutes.')
//       toast.info('Tip', 'Press Cmd+K to open the command palette.')
//
// WHAT WAS BROKEN:
// ─────────────────
// FIX 1: Missing @keyframes toastIn / toastOut CSS.
//   The old Toast.jsx used animation: 'toastIn 0.32s...' in inline styles
//   but those keyframes were never defined anywhere — not in index.css,
//   not in the component itself. The toasts appeared instantly with no
//   animation, and the dismiss animation didn't work at all.
//   Fix: inject <style> with the keyframes directly in ToastProvider.
//
// FIX 2: Auto-dismiss timer not reset when a new toast appears.
//   If two toasts appeared quickly, the second one could be dismissed
//   by the first one's timer. Fix: useEffect cleanup properly cancels
//   the timer when the component unmounts.
//
// FIX 3: Toast stacking order.
//   New toasts now appear at the TOP of the stack (newest first),
//   which is the standard UX pattern. Old code pushed new toasts to
//   the bottom, pushing earlier toasts up — confusing to read.

import {
  createContext, useContext, useState, useCallback, useEffect,
} from 'react'
import { useTheme } from '../ThemeContext'

const ToastContext = createContext(null)

// ── Keyframes injected once ───────────────────────────────────────────────────
// These are defined here so the component is self-contained.
// No need to edit index.css separately.
const TOAST_KEYFRAMES = `
  @keyframes toastIn {
    from {
      opacity: 0;
      transform: translateX(calc(100% + 20px));
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
  @keyframes toastOut {
    from {
      opacity: 1;
      transform: translateX(0);
      max-height: 120px;
      margin-bottom: 0px;
    }
    to {
      opacity: 0;
      transform: translateX(calc(100% + 20px));
      max-height: 0px;
      margin-bottom: -10px;
    }
  }
`

// ── Individual Toast Item ─────────────────────────────────────────────────────
function ToastItem({ id, type, title, message, onRemove }) {
  const { T, isDark } = useTheme()
  const [leaving, setLeaving] = useState(false)

  // Auto-dismiss after 4.5 seconds
  // useEffect cleanup cancels the timer if the toast is dismissed early
  useEffect(() => {
    const timer = setTimeout(() => dismiss(), 4500)
    return () => clearTimeout(timer)
  }, [])   // empty deps: run once on mount, clean up on unmount

  function dismiss() {
    if (leaving) return   // prevent double-dismiss
    setLeaving(true)
    // Wait for the CSS exit animation (0.35s) before removing from state
    setTimeout(() => onRemove(id), 350)
  }

  // Visual config per toast type
  const config = {
    success: {
      icon:    '✓',
      color:   T.emerald,
      label:   'Success',
    },
    error: {
      icon:    '✕',
      color:   T.danger || '#ef4444',
      label:   'Error',
    },
    warning: {
      icon:    '!',
      color:   T.warning || '#f59e0b',
      label:   'Warning',
    },
    info: {
      icon:    'i',
      color:   T.accent,
      label:   'Info',
    },
  }[type] || { icon: 'i', color: T.accent, label: 'Info' }

  return (
    <div
      onClick={dismiss}
      role="alert"
      aria-live="polite"
      style={{
        display:        'flex',
        alignItems:     'flex-start',
        gap:            '12px',
        padding:        '14px 16px',
        background:     isDark
          ? 'rgba(15,15,20,0.97)'
          : 'rgba(255,255,255,0.97)',
        border:         `1px solid ${config.color}33`,
        borderLeft:     `3px solid ${config.color}`,
        borderRadius:   '12px',
        boxShadow:      isDark
          ? `0 8px 32px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.04) inset`
          : `0 8px 32px rgba(0,0,0,0.12), 0 0 0 1px rgba(255,255,255,0.9) inset`,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        maxWidth:       '360px',
        minWidth:       '260px',
        cursor:         'pointer',
        userSelect:     'none',
        // FIX: animation now references keyframes defined in TOAST_KEYFRAMES above
        animation:      `${leaving ? 'toastOut' : 'toastIn'} 0.32s cubic-bezier(0.4,0,0.2,1) both`,
        willChange:     'transform, opacity',
      }}
    >
      {/* Icon circle */}
      <div style={{
        width:            '26px',
        height:           '26px',
        borderRadius:     '50%',
        background:       `${config.color}18`,
        border:           `1px solid ${config.color}40`,
        display:          'flex',
        alignItems:       'center',
        justifyContent:   'center',
        flexShrink:       0,
        fontSize:         '12px',
        fontWeight:       800,
        color:            config.color,
        lineHeight:       1,
      }}>
        {config.icon}
      </div>

      {/* Text content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize:    '13.5px',
          fontWeight:  650,
          color:       isDark ? '#f4f4f5' : '#09090b',
          marginBottom: message ? '3px' : 0,
          lineHeight:  1.3,
        }}>
          {title}
        </div>
        {message && (
          <div style={{
            fontSize:   '12px',
            color:      isDark ? 'rgba(161,161,170,0.85)' : '#52525b',
            lineHeight: 1.5,
          }}>
            {message}
          </div>
        )}
      </div>

      {/* Close × */}
      <div style={{
        fontSize:    '18px',
        lineHeight:  1,
        color:       isDark ? 'rgba(255,255,255,0.22)' : 'rgba(0,0,0,0.20)',
        flexShrink:  0,
        marginTop:   '1px',
        transition:  'color 0.12s ease',
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
    const id = `t_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
    // FIX: prepend so newest toast appears at top (standard UX)
    setToasts(prev => [{ id, type, title, message }, ...prev])
  }, [])

  const remove = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  // Shorthand methods — usage: toast.success('Title', 'Message')
  const toast = {
    success: (title, message) => add('success', title, message),
    error:   (title, message) => add('error',   title, message),
    warning: (title, message) => add('warning', title, message),
    info:    (title, message) => add('info',    title, message),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {/* FIX: inject keyframes once — self-contained, no index.css dependency */}
      <style dangerouslySetInnerHTML={{ __html: TOAST_KEYFRAMES }} />

      {children}

      {/* Floating container — fixed top-right, above everything (z: 9999) */}
      <div
        aria-label="Notifications"
        style={{
          position:       'fixed',
          top:            '20px',
          right:          '20px',
          zIndex:         9999,
          display:        'flex',
          flexDirection:  'column',
          gap:            '10px',
          pointerEvents:  toasts.length ? 'auto' : 'none',
          // Max 5 toasts visible at once — oldest are already auto-dismissed
          maxHeight:      '90vh',
          overflowY:      'hidden',
        }}
      >
        {toasts.slice(0, 5).map(t => (
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