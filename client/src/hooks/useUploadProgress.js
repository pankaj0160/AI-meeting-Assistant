// client/src/hooks/useUploadProgress.js
//
// WHAT THIS HOOK DOES:
// ────────────────────
// Manages the upload progress overlay.
//
// ROOT CAUSE OF THE STUCK SPINNER (now fixed):
// ─────────────────────────────────────────────
// The upload/youtube endpoints are SYNCHRONOUS — they process the entire
// meeting (download → transcribe → intelligence → index) and then return
// the final response with meeting_id when everything is done.
//
// Old approach: hook ignored the POST response, instead polled
//   GET /jobs/{id}/status (Redis) for progress updates.
//   Problem: Redis isn't running in Windows dev, so every poll
//   returned 404. The spinner spun forever even though the meeting
//   was already fully processed.
//
// New approach (this file): the hook receives meeting_id directly
//   from the POST response. No Redis, no polling, no job status.
//   The progress steps animate while the POST is in-flight.
//   When POST resolves → navigate to meeting immediately.
//
// PROGRESS ANIMATION without Redis:
//   Since we don't have real step-by-step updates, we simulate
//   progress with a timed animation. Steps advance automatically
//   every N seconds to give visual feedback during the long wait.
//   When the POST resolves, we jump to 100% and navigate.

import { useState, useRef, useCallback, useEffect } from 'react'

export const STEPS = [
  { id: 'download',   label: 'Downloading audio',       icon: '⬇️', duration: 15000 },
  { id: 'extract',    label: 'Extracting audio',        icon: '🔊', duration: 10000 },
  { id: 'transcribe', label: 'Transcribing speech',     icon: '📝', duration: 60000 },
  { id: 'intel',      label: 'Generating intelligence', icon: '🤖', duration: 20000 },
  { id: 'index',      label: 'Indexing for search',     icon: '🔍', duration: 5000  },
  { id: 'done',       label: 'Complete',                icon: '✅', duration: 0     },
]

export function useUploadProgress() {
  const [active,  setActive]  = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [pct,     setPct]     = useState(0)
  const [error,   setError]   = useState(null)

  const timerRef   = useRef(null)
  const resolveRef = useRef(null)   // holds the resolve fn for the promise

  // Advance through steps automatically while POST is in-flight
  const advanceStep = useCallback((idx) => {
    if (idx >= STEPS.length - 1) return   // don't advance past "done"
    const step = STEPS[idx]
    if (!step || step.duration === 0) return

    timerRef.current = setTimeout(() => {
      setStepIdx(idx + 1)
      setPct(Math.min(95, Math.round(((idx + 1) / (STEPS.length - 1)) * 95)))
      advanceStep(idx + 1)
    }, step.duration)
  }, [])

  const stopTimers = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // Called by Upload.jsx before making the POST request
  const start = useCallback(() => {
    setActive(true)
    setStepIdx(0)
    setPct(5)
    setError(null)
    advanceStep(0)
  }, [advanceStep])

  // Called by Upload.jsx when the POST response comes back with meeting_id
  // Stops the animation, jumps to done, returns meeting_id
  const complete = useCallback((meetingId) => {
    stopTimers()
    setStepIdx(STEPS.length - 1)
    setPct(100)
    setTimeout(() => {
      setActive(false)
      if (resolveRef.current) {
        resolveRef.current(meetingId)
        resolveRef.current = null
      }
    }, 800)   // brief pause so user sees 100%
  }, [stopTimers])

  const fail = useCallback((message) => {
    stopTimers()
    setError(message)
    setActive(false)
  }, [stopTimers])

  const reset = useCallback(() => {
    stopTimers()
    setActive(false)
    setStepIdx(0)
    setPct(0)
    setError(null)
  }, [stopTimers])

  // Cleanup on unmount
  useEffect(() => () => stopTimers(), [stopTimers])

  const currentStep = STEPS[stepIdx] || STEPS[0]

  return {
    active,
    step:    currentStep.id,
    message: currentStep.label,
    pct,
    error,
    start,
    complete,
    fail,
    reset,
    // Legacy alias used by Upload.jsx
    finish:  complete,
  }
}