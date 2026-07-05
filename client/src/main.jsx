// client/src/main.jsx

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { ThemeProvider } from './ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { WorkspaceProvider } from './context/WorkspaceContext'
import ErrorBoundary from './components/ErrorBoundary'
import { ToastProvider } from './components/Toast'
import { CommandPaletteProvider } from './components/CommandPalette'
import { initSentry } from './lib/sentry'

// PHASE 1: error monitoring. No-op if VITE_SENTRY_DSN isn't set (see
// src/lib/sentry.js) — safe to call unconditionally on every app start.
initSentry()

// FIX: Wrap the entire app in an ErrorBoundary.
//
// Without this: any unhandled error in any component crashes the whole
// app to a blank white page with no message. User is completely stuck.
//
// With this: if something truly catastrophic happens at the root level
// (e.g. AuthContext itself crashes), the user sees a friendly error screen
// with a "Reload page" button instead of a white void.
//
// This is the LAST RESORT boundary — it catches anything that slips
// through the page-level boundaries in App.jsx.
//
// showHome=false because at this level the whole app is broken,
// navigating "home" won't help — only a full reload will.

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary
      fallbackTitle="Summly ran into a problem"
      fallbackMessage="Something unexpected happened. Reloading the page usually fixes this."
      showHome={false}
    >
      <ThemeProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </WorkspaceProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  </StrictMode>
)