// client/src/hooks/useUploadProgress.js

import { useState, useRef, useCallback } from 'react'

const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'

const WS_BASE = API_BASE
  .replace(/^https/, 'wss')
  .replace(/^http/, 'ws')



export const STEPS = [
  { id: 'download',   label: 'Downloading audio',          icon: '⬇️' },
  { id: 'extract',    label: 'Extracting audio',           icon: '🔊' },
  { id: 'transcribe', label: 'Transcribing speech',        icon: '📝' },
  { id: 'intel',      label: 'Generating intelligence',    icon: '🤖' },
  { id: 'index',      label: 'Indexing for search',        icon: '🔍' },
  { id: 'done',       label: 'Complete',                   icon: '✅' },
]

export function useUploadProgress() {
  const [active,   setActive]   = useState(false)
  const [step,     setStep]     = useState(null)
  const [message,  setMessage]  = useState('')
  const [pct,      setPct]      = useState(0)
  const [error,    setError]    = useState(null)
  const wsRef = useRef(null)

  // Generate unique job ID
  const newJobId = () =>
    `job_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

  const connect = useCallback((jobId) => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${WS_BASE}/ws/progress/${jobId}`)
      wsRef.current = ws

      ws.onopen    = () => resolve(ws)
      ws.onerror   = () => reject(new Error('WebSocket connection failed'))

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          setStep(data.step)
          setMessage(data.message)
          setPct(data.pct)
          if (data.step === 'error') {
            setError(data.message)
            setActive(false)
          }
        } catch {}
      }
    })
  }, [])

  const start = useCallback(async () => {
    const jobId = newJobId()
    setActive(true)
    setError(null)
    setStep(null)
    setPct(0)
    setMessage('Connecting...')
    await connect(jobId)
    return jobId
  }, [connect])

  const finish = useCallback(() => {
    setActive(false)
    wsRef.current?.close()
  }, [])

  const reset = useCallback(() => {
    setActive(false)
    setStep(null)
    setMessage('')
    setPct(0)
    setError(null)
    wsRef.current?.close()
  }, [])

  return { active, step, message, pct, error, start, finish, reset }
}