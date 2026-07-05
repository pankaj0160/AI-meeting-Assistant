// src/lib/sentry.js
//
// PHASE 1: frontend error monitoring.
//
// Mirrors the backend pattern in server/main.py: if no DSN is configured,
// everything here becomes a no-op — the app runs exactly as it did before,
// nothing crashes, nothing is required to run locally.
//
// Requires @sentry/react to be installed (added to package.json). Unlike
// the backend's try/except import pattern, JS bundlers resolve imports at
// build time, so this always imports the package — it just skips calling
// .init() when there's no DSN, and every export below degrades to a no-op.

import * as Sentry from '@sentry/react'

const DSN = import.meta.env.VITE_SENTRY_DSN

export function initSentry() {
  if (!DSN) {
    // No DSN set — expected in local dev. Nothing to do.
    return
  }
  Sentry.init({
    dsn: DSN,
    environment: import.meta.env.MODE, // 'development' | 'production'
    // Sample a fraction of transactions for performance monitoring —
    // keep this low, raise only while actively debugging.
    tracesSampleRate: 0.1,
    // Don't record session replays by default — meeting content and
    // transcripts could appear on screen during a session.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
  })
}

/**
 * Safe wrapper around Sentry.captureException — never throws, and is a
 * silent no-op when Sentry isn't configured (DSN not set).
 */
export function captureException(error, context) {
  if (!DSN) return
  try {
    Sentry.captureException(error, context)
  } catch {
    // Reporting the error must never itself throw inside an ErrorBoundary.
  }
}