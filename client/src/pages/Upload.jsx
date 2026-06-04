// client/src/pages/Upload.jsx

import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Upload as UploadIcon, Play, FileAudio,
  FileVideo, X, AlertCircle, ArrowRight, CheckCircle,
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useUploadProgress, STEPS } from '../hooks/useUploadProgress'
import { PageHeader, Card, Button, Divider } from '../components/ui'
import { getToken } from '../api/client'

const AUDIO_EXTS = ['mp3', 'wav', 'm4a', 'aac', 'flac']
const VIDEO_EXTS = ['mp4', 'mkv', 'avi', 'mov', 'webm']
const ALL_EXTS   = [...AUDIO_EXTS, ...VIDEO_EXTS]

function fmtSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ── Progress overlay ───────────────────────────────────────────────────────────
function ProgressOverlay({ pct, step, message, T }) {
  const currentIdx = STEPS.findIndex(s => s.id === step)
  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.75)',
      backdropFilter: 'blur(10px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 999,
    }}>
      <div className="anim-fade-up" style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: '22px',
        padding: '40px 48px',
        width: '420px',
        boxShadow: '0 32px 80px rgba(0,0,0,0.5)',
      }}>
        <div style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.04em', color: T.text, marginBottom: '5px' }}>
          Processing Meeting
        </div>
        <div style={{ fontSize: '13px', color: T.text3, marginBottom: '28px' }}>
          {message || 'Please wait...'}
        </div>

        {/* Progress bar */}
        <div style={{ height: '5px', borderRadius: '99px', background: T.surface2, marginBottom: '28px', overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: T.btnGrad, borderRadius: '99px',
            transition: 'width 0.6s ease',
          }} />
        </div>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '11px' }}>
          {STEPS.map((s, i) => {
            const done   = i < currentIdx
            const active = i === currentIdx
            return (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '50%', flexShrink: 0,
                  background: done ? T.emeraldBg : active ? T.accentBg : T.surface2,
                  border: `2px solid ${done ? T.emerald : active ? T.accent : T.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.3s ease',
                }}>
                  {done
                    ? <CheckCircle size={13} color={T.emerald} />
                    : active
                      ? <div className="spinner" style={{ width: '12px', height: '12px', borderColor: T.accent, borderTopColor: 'transparent' }} />
                      : <span style={{ fontSize: '11px' }}>{s.icon}</span>
                  }
                </div>
                <div style={{ flex: 1, fontSize: '13px', fontWeight: active ? 650 : done ? 500 : 400, color: done ? T.emerald : active ? T.text : T.text4, transition: 'color 0.3s ease' }}>
                  {s.label}
                </div>
                {active && (
                  <span style={{ fontSize: '12px', fontWeight: 700, color: T.accent }}>{pct}%</span>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────
export default function Upload() {
  const { T }    = useTheme()
  const navigate = useNavigate()
  const inputRef = useRef()
  const prog     = useUploadProgress()

  const [file,     setFile]     = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [ytUrl,    setYtUrl]    = useState('')
  const [tab,      setTab]      = useState('file')
  const [error,    setError]    = useState(null)

  const validateAndSetFile = (f) => {
    const ext = f.name.split('.').pop().toLowerCase()
    if (!ALL_EXTS.includes(ext)) { setError(`Unsupported format: .${ext}`); return }
    setError(null)
    setFile(f)
  }

  const handleDrop = useCallback(e => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) validateAndSetFile(dropped)
  }, [])

  const handleFileSubmit = async () => {
    if (!file) return
    setError(null)
    try {
      const jobId = await prog.start()
      const token = getToken()
      const form  = new FormData()
      form.append('file', file)
      const res = await fetch(`/api/upload/progress?job_id=${jobId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.error || `HTTP ${res.status}`) }
      const data = await res.json()
      prog.finish()
      await new Promise(r => setTimeout(r, 800))
      navigate(`/app/meetings/${data.meeting_id}`)
    } catch (e) { setError(e.message); prog.reset() }
  }

  const handleYouTubeSubmit = async () => {
    if (!ytUrl.trim()) return
    setError(null)
    try {
      const jobId = await prog.start()
      const token = getToken()
      const res = await fetch(`/api/youtube/progress?job_id=${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ url: ytUrl.trim(), job_id: jobId }),
      })
      if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.error || `HTTP ${res.status}`) }
      const data = await res.json()
      prog.finish()
      await new Promise(r => setTimeout(r, 800))
      navigate(`/app/meetings/${data.meeting_id}`)
    } catch (e) { setError(e.message); prog.reset() }
  }

  const tabStyle = (active) => ({
    padding: '8px 16px', borderRadius: '8px',
    fontSize: '13px', fontWeight: active ? 650 : 450,
    color: active ? T.text : T.text3,
    background: active ? T.surface : 'transparent',
    border: `1px solid ${active ? T.border : 'transparent'}`,
    cursor: 'pointer', transition: 'all 0.15s ease',
    boxShadow: active ? T.cardShadow : 'none',
    display: 'flex', alignItems: 'center', gap: '6px',
    fontFamily: 'var(--font)',
  })

  return (
    <div>
      {prog.active && <ProgressOverlay pct={prog.pct} step={prog.step} message={prog.message} T={T} />}

      <PageHeader
        title="Upload Meeting"
        subtitle="Upload a file or paste a YouTube URL to transcribe and analyze."
      />

      {/* ── Centered content column ── */}
      <div style={{ maxWidth: '680px', margin: '0 auto' }}>

        {/* Tab switcher */}
        <div style={{
          display: 'inline-flex',
          background: T.surface2, border: `1px solid ${T.border}`,
          borderRadius: '11px', padding: '4px', gap: '4px',
          marginBottom: '20px',
        }}>
          <button style={tabStyle(tab === 'file')}    onClick={() => { setTab('file');    setError(null) }}>
            <UploadIcon size={13} /> File Upload
          </button>
          <button style={tabStyle(tab === 'youtube')} onClick={() => { setTab('youtube'); setError(null) }}>
            <Play size={13} /> YouTube URL
          </button>
        </div>

        {/* ── File tab ── */}
        {tab === 'file' && (
          <div className="anim-fade-in">
            <Card style={{ padding: 0, overflow: 'hidden' }}>

              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => !file && inputRef.current?.click()}
                style={{
                  padding: file ? '20px 24px' : '48px 32px',
                  textAlign: 'center',
                  cursor: file ? 'default' : 'pointer',
                  background: dragOver ? T.accentHover : 'transparent',
                  borderBottom: file ? `1px solid ${T.border}` : 'none',
                  transition: 'background 0.15s ease',
                }}
              >
                <input
                  ref={inputRef} type="file"
                  accept={ALL_EXTS.map(e => `.${e}`).join(',')}
                  style={{ display: 'none' }}
                  onChange={e => e.target.files[0] && validateAndSetFile(e.target.files[0])}
                />

                {!file ? (
                  <>
                    <div style={{
                      width: '56px', height: '56px', borderRadius: '14px',
                      background: dragOver ? T.accentBg : T.surface2,
                      border: `2px dashed ${dragOver ? T.accent : T.border2}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      margin: '0 auto 16px', transition: 'all 0.15s ease',
                    }}>
                      <UploadIcon size={22} color={dragOver ? T.accent : T.text3} strokeWidth={1.8} />
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: T.text, letterSpacing: '-0.03em', marginBottom: '5px' }}>
                      Drop your file here
                    </div>
                    <div style={{ fontSize: '13px', color: T.text3, marginBottom: '16px' }}>
                      or click to browse
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', justifyContent: 'center' }}>
                      {['MP3','WAV','MP4','M4A','MKV','WEBM'].map(ext => (
                        <span key={ext} style={{
                          padding: '2px 8px', borderRadius: '99px',
                          fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em',
                          color: T.text3, background: T.surface2, border: `1px solid ${T.border}`,
                        }}>
                          {ext}
                        </span>
                      ))}
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '13px', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: T.accentBg, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <FileAudio size={18} color={T.accentLight} />
                      </div>
                      <div style={{ textAlign: 'left' }}>
                        <div style={{ fontSize: '14px', fontWeight: 600, color: T.text, marginBottom: '2px' }}>{file.name}</div>
                        <div style={{ fontSize: '12px', color: T.text3 }}>{fmtSize(file.size)}</div>
                      </div>
                    </div>
                    <button
                      onClick={e => { e.stopPropagation(); setFile(null) }}
                      style={{ background: T.dangerBg, border: 'none', borderRadius: '7px', width: '28px', height: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: T.danger, flexShrink: 0 }}
                    >
                      <X size={12} />
                    </button>
                  </div>
                )}
              </div>

              {/* Submit row */}
              {file && (
                <div style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: '13px', color: T.text3 }}>Ready to process</div>
                  <Button icon={<ArrowRight size={14} />} onClick={handleFileSubmit} loading={prog.active}>
                    Transcribe & Analyze
                  </Button>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ── YouTube tab ── */}
        {tab === 'youtube' && (
          <div className="anim-fade-in">
            <Card style={{ padding: '24px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: T.dangerBg, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Play size={18} color={T.danger} />
                </div>
                <div>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>YouTube Video</div>
                  <div style={{ fontSize: '12.5px', color: T.text3, marginTop: '2px' }}>Paste any YouTube URL to transcribe and analyze</div>
                </div>
              </div>

              <input
                type="text"
                value={ytUrl}
                onChange={e => setYtUrl(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleYouTubeSubmit()}
                placeholder="https://www.youtube.com/watch?v=..."
                style={{
                  width: '100%', padding: '11px 14px', borderRadius: '10px',
                  border: `1px solid ${ytUrl ? T.borderFocus : T.inputBorder}`,
                  background: T.inputBg, color: T.text, fontSize: '14px', outline: 'none',
                  marginBottom: '16px', transition: 'border-color 0.15s ease',
                  boxShadow: ytUrl ? `0 0 0 3px ${T.accentBg}` : 'none',
                  fontFamily: 'var(--font)',
                  boxSizing: 'border-box',
                }}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button icon={<ArrowRight size={14} />} onClick={handleYouTubeSubmit} disabled={!ytUrl.trim()} loading={prog.active}>
                  Download & Analyze
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* ── Error banner ── */}
        {error && (
          <div className="anim-fade-up" style={{
            display: 'flex', alignItems: 'flex-start', gap: '10px',
            padding: '12px 16px', marginTop: '12px',
            background: T.dangerBg, border: `1px solid ${T.danger}44`,
            borderRadius: '10px',
          }}>
            <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0, marginTop: '1px' }} />
            <div style={{ fontSize: '13px', color: T.danger, lineHeight: 1.5 }}>{error}</div>
          </div>
        )}

        <Divider />

        {/* ── Supported formats ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
          {[
            { icon: <FileAudio size={16} color={T.blueText} />,  bg: T.blueBg,   label: 'Audio Files', formats: 'MP3, WAV, M4A, AAC, FLAC' },
            { icon: <FileVideo size={16} color={T.purpleText} />, bg: T.purpleBg, label: 'Video Files', formats: 'MP4, MKV, AVI, MOV, WEBM' },
          ].map(item => (
            <div key={item.label} style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '13px 15px',
              background: T.surface, border: `1px solid ${T.border}`,
              borderRadius: '11px',
            }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: item.bg, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {item.icon}
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: T.text, marginBottom: '2px' }}>{item.label}</div>
                <div style={{ fontSize: '11.5px', color: T.text3 }}>{item.formats}</div>
              </div>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}