// components/ErrorBoundary.jsx
//
// What is an Error Boundary?
//   A component that catches JavaScript errors from any child component.
//   Without this, any runtime error in React unmounts the entire app
//   and shows a blank white page — the "white screen of death".
//
// Why a CLASS component?
//   Error Boundaries must use componentDidCatch() — a lifecycle method
//   that only exists in class components. This is one of the very few
//   cases where you still need a class component in modern React.
//   Function components with hooks cannot catch render errors.
//
// How to use it:
//   Wrap any component you want to protect:
//     <ErrorBoundary>
//       <Dashboard />
//     </ErrorBoundary>
//
//   If Dashboard throws → ErrorBoundary shows the fallback UI instead.
//   The rest of the app (sidebar, navbar) keeps working normally.

import { Component } from 'react'
import { captureException } from '../lib/sentry'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    // hasError: true means "show fallback UI instead of children"
    // error:    the actual Error object that was thrown
    this.state = { hasError: false, error: null }
  }

  // React calls this static method when a child throws.
  // We return new state — React merges it in automatically.
  // This runs BEFORE render() so the fallback appears immediately.
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  // React calls this AFTER the error is caught.
  // Use it for logging — send the error to your monitoring service.
  componentDidCatch(error, info) {
    // info.componentStack is the React component tree that led to the error
    // Very useful for debugging — shows exactly which component crashed
    console.error('[ErrorBoundary] Caught error:', error)
    console.error('[ErrorBoundary] Component stack:', info.componentStack)
    // PHASE 1: forward to Sentry. No-op if VITE_SENTRY_DSN isn't set,
    // so this is always safe to call.
    captureException(error, { extra: { componentStack: info.componentStack } })
  }

  handleReset() {
    // Clear the error state — React will try to render children again.
    // If the error was temporary (e.g. network blip) this may recover.
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (!this.state.hasError) {
      // No error — render children normally, nothing changes
      return this.props.children
    }

    // Error caught — show the fallback UI instead of the crashed component.
    // We intentionally do NOT show the raw error.message to the user:
    //   - It may contain internal paths, variable names, or confusing tech jargon
    //   - It gives attackers hints about your code structure
    // We show a friendly message. The real error is in the console.

    const { fallbackTitle, fallbackMessage, showHome = true } = this.props

    return (
      <div style={{
        display:        'flex',
        flexDirection:  'column',
        alignItems:     'center',
        justifyContent: 'center',
        minHeight:      '60vh',
        padding:        '40px 24px',
        textAlign:      'center',
        fontFamily:     'var(--font-body, system-ui)',
      }}>

        {/* Icon */}
        <div style={{
          fontSize:     '48px',
          marginBottom: '16px',
          lineHeight:   1,
        }}>
          ⚠️
        </div>

        {/* Title */}
        <h2 style={{
          fontSize:      '20px',
          fontWeight:    700,
          color:         'var(--color-text-primary, #111)',
          marginBottom:  '8px',
          letterSpacing: '-0.02em',
        }}>
          {fallbackTitle || 'Something went wrong'}
        </h2>

        {/* Message */}
        <p style={{
          fontSize:     '14px',
          color:        'var(--color-text-secondary, #666)',
          maxWidth:     '380px',
          lineHeight:   1.6,
          marginBottom: '28px',
        }}>
          {fallbackMessage ||
            "This section ran into an unexpected error. You can try reloading, or go back to the dashboard."}
        </p>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'center' }}>

          {/* Try again — resets error state and re-renders children */}
          <button
            onClick={() => this.handleReset()}
            style={{
              padding:      '9px 18px',
              borderRadius: '10px',
              border:       '1px solid #e2e8f0',
              background:   'white',
              color:        '#374151',
              fontSize:     '13.5px',
              fontWeight:   600,
              cursor:       'pointer',
              fontFamily:   'inherit',
            }}
          >
            Try again
          </button>

          {/* Reload — full page reload, clears all React state */}
          <button
            onClick={() => window.location.reload()}
            style={{
              padding:      '9px 18px',
              borderRadius: '10px',
              border:       'none',
              background:   '#059669',
              color:        'white',
              fontSize:     '13.5px',
              fontWeight:   600,
              cursor:       'pointer',
              fontFamily:   'inherit',
              boxShadow:    '0 4px 14px rgba(5,150,105,0.30)',
            }}
          >
            Reload page
          </button>

          {/* Go home — only shown when wrapping a page, not the whole app */}
          {showHome && (
            <button
              onClick={() => window.location.href = '/app'}
              style={{
                padding:      '9px 18px',
                borderRadius: '10px',
                border:       '1px solid #e2e8f0',
                background:   'white',
                color:        '#374151',
                fontSize:     '13.5px',
                fontWeight:   600,
                cursor:       'pointer',
                fontFamily:   'inherit',
              }}
            >
              Go to Dashboard
            </button>
          )}
        </div>

        {/* Dev-only error detail — hidden in production */}
        {import.meta.env.DEV && this.state.error && (
          <details style={{
            marginTop:  '32px',
            maxWidth:   '600px',
            textAlign:  'left',
            fontSize:   '11px',
            color:      '#9ca3af',
            fontFamily: 'var(--font-mono, monospace)',
          }}>
            <summary style={{ cursor: 'pointer', marginBottom: '8px', color: '#6b7280' }}>
              Developer details (hidden in production)
            </summary>
            <pre style={{
              background:   '#f9fafb',
              padding:      '12px',
              borderRadius: '8px',
              overflow:     'auto',
              whiteSpace:   'pre-wrap',
              wordBreak:    'break-word',
              border:       '1px solid #e5e7eb',
            }}>
              {this.state.error.toString()}
              {'\n\n'}
              {this.state.error.stack}
            </pre>
          </details>
        )}

      </div>
    )
  }
}